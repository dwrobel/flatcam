############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
############################################################

import copy
import inspect  # TODO: For debugging only.
from datetime import datetime

from flatcamGUI.ObjectUI import *
from FlatCAMCommon import LoudDict
from camlib import *
import itertools

import gettext
import FlatCAMTranslation as fcTranslate

fcTranslate.apply_language('strings')
import builtins
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ObjectDeleted(Exception):
    # Interrupts plotting process if FlatCAMObj has been deleted
    pass


class ValidationError(Exception):
    def __init__(self, message, errors):
        super().__init__(message)

        self.errors = errors

########################################
##            FlatCAMObj              ##
########################################


class FlatCAMObj(QtCore.QObject):
    """
    Base type of objects handled in FlatCAM. These become interactive
    in the GUI, can be plotted, and their options can be modified
    by the user in their respective forms.
    """

    # Instance of the application to which these are related.
    # The app should set this value.
    app = None

    def __init__(self, name):
        """
        Constructor.

        :param name: Name of the object given by the user.
        :return: FlatCAMObj
        """
        QtCore.QObject.__init__(self)

        # View
        self.ui = None

        self.options = LoudDict(name=name)
        self.options.set_change_callback(self.on_options_change)

        self.form_fields = {}

        self.kind = None  # Override with proper name

        # self.shapes = ShapeCollection(parent=self.app.plotcanvas.vispy_canvas.view.scene)
        self.shapes = self.app.plotcanvas.new_shape_group()

        self.mark_shapes = self.app.plotcanvas.new_shape_collection(layers=2)

        self.item = None  # Link with project view item

        self.muted_ui = False
        self.deleted = False

        self._drawing_tolerance = 0.01

        self.isHovering = False
        self.notHovering = True

        # assert isinstance(self.ui, ObjectUI)
        # self.ui.name_entry.returnPressed.connect(self.on_name_activate)
        # self.ui.offset_button.clicked.connect(self.on_offset_button_click)
        # self.ui.scale_button.clicked.connect(self.on_scale_button_click)

    def __del__(self):
        pass

    def __str__(self):
        return "<FlatCAMObj({:12s}): {:20s}>".format(self.kind, self.options["name"])

    def from_dict(self, d):
        """
        This supersedes ``from_dict`` in derived classes. Derived classes
        must inherit from FlatCAMObj first, then from derivatives of Geometry.

        ``self.options`` is only updated, not overwritten. This ensures that
        options set by the app do not vanish when reading the objects
        from a project file.

        :param d: Dictionary with attributes to set.
        :return: None
        """

        for attr in self.ser_attrs:

            if attr == 'options':
                self.options.update(d[attr])
            else:
                try:
                    setattr(self, attr, d[attr])
                except KeyError:
                    log.debug("FlatCAMObj.from_dict() --> KeyError: %s. Means that we are loading an old project that don't"
                              "have all attributes in the latest FlatCAM." % str(attr))
                    pass

    def on_options_change(self, key):
        # Update form on programmatically options change
        self.set_form_item(key)

        # Set object visibility
        if key == 'plot':
            self.visible = self.options['plot']

        # self.emit(QtCore.SIGNAL("optionChanged"), key)
        self.optionChanged.emit(key)

    def set_ui(self, ui):
        self.ui = ui

        self.form_fields = {"name": self.ui.name_entry}

        assert isinstance(self.ui, ObjectUI)
        self.ui.name_entry.returnPressed.connect(self.on_name_activate)
        self.ui.offset_button.clicked.connect(self.on_offset_button_click)
        self.ui.scale_button.clicked.connect(self.on_scale_button_click)

        self.ui.offsetvector_entry.returnPressed.connect(self.on_offset_button_click)
        self.ui.scale_entry.returnPressed.connect(self.on_scale_button_click)
        # self.ui.skew_button.clicked.connect(self.on_skew_button_click)

    def build_ui(self):
        """
        Sets up the UI/form for this object. Show the UI
        in the App.

        :return: None
        :rtype: None
        """

        self.muted_ui = True
        FlatCAMApp.App.log.debug(str(inspect.stack()[1][3]) + "--> FlatCAMObj.build_ui()")

        # Remove anything else in the box
        # box_children = self.app.ui.notebook.selected_contents.get_children()
        # for child in box_children:
        #     self.app.ui.notebook.selected_contents.remove(child)
        # while self.app.ui.selected_layout.count():
        #     self.app.ui.selected_layout.takeAt(0)

        # Put in the UI
        # box_selected.pack_start(sw, True, True, 0)
        # self.app.ui.notebook.selected_contents.add(self.ui)
        # self.app.ui.selected_layout.addWidget(self.ui)
        try:
            self.app.ui.selected_scroll_area.takeWidget()
        except:
            self.app.log.debug("Nothing to remove")
        self.app.ui.selected_scroll_area.setWidget(self.ui)

        self.muted_ui = False

    def on_name_activate(self):
        old_name = copy.copy(self.options["name"])
        new_name = self.ui.name_entry.get_value()

        # update the SHELL auto-completer model data
        try:
            self.app.myKeywords.remove(old_name)
            self.app.myKeywords.append(new_name)
            self.app.shell._edit.set_model_data(self.app.myKeywords)
        except:
            log.debug("on_name_activate() --> Could not remove the old object name from auto-completer model list")

        self.options["name"] = self.ui.name_entry.get_value()
        self.app.inform.emit(_("[success]Name changed from %s to %s") % (old_name, new_name))

    def on_offset_button_click(self):
        self.app.report_usage("obj_on_offset_button")

        self.read_form()
        vect = self.ui.offsetvector_entry.get_value()
        self.offset(vect)
        self.plot()
        self.app.object_changed.emit(self)

    def on_scale_button_click(self):
        self.app.report_usage("obj_on_scale_button")
        self.read_form()
        factor = self.ui.scale_entry.get_value()
        self.scale(factor)
        self.plot()
        self.app.object_changed.emit(self)

    def on_skew_button_click(self):
        self.app.report_usage("obj_on_skew_button")
        self.read_form()
        xangle = self.ui.xangle_entry.get_value()
        yangle = self.ui.yangle_entry.get_value()
        self.skew(xangle, yangle)
        self.plot()
        self.app.object_changed.emit(self)

    def to_form(self):
        """
        Copies options to the UI form.

        :return: None
        """
        FlatCAMApp.App.log.debug(str(inspect.stack()[1][3]) + " --> FlatCAMObj.to_form()")
        for option in self.options:
            try:
                self.set_form_item(option)
            except:
                self.app.log.warning("Unexpected error:", sys.exc_info())

    def read_form(self):
        """
        Reads form into ``self.options``.

        :return: None
        :rtype: None
        """
        FlatCAMApp.App.log.debug(str(inspect.stack()[1][3]) + "--> FlatCAMObj.read_form()")
        for option in self.options:
            try:
                self.read_form_item(option)
            except:
                self.app.log.warning("Unexpected error:", sys.exc_info())

    def set_form_item(self, option):
        """
        Copies the specified option to the UI form.

        :param option: Name of the option (Key in ``self.options``).
        :type option: str
        :return: None
        """

        try:
            self.form_fields[option].set_value(self.options[option])
        except KeyError:
            # self.app.log.warn("Tried to set an option or field that does not exist: %s" % option)
            pass

    def read_form_item(self, option):
        """
        Reads the specified option from the UI form into ``self.options``.

        :param option: Name of the option.
        :type option: str
        :return: None
        """

        try:
            self.options[option] = self.form_fields[option].get_value()
        except KeyError:
            self.app.log.warning("Failed to read option from field: %s" % option)

    def plot(self):
        """
        Plot this object (Extend this method to implement the actual plotting).
        Call this in descendants before doing the plotting.

        :return: Whether to continue plotting or not depending on the "plot" option.
        :rtype: bool
        """
        FlatCAMApp.App.log.debug(str(inspect.stack()[1][3]) + " --> FlatCAMObj.plot()")

        if self.deleted:
            return False

        self.clear()


        return True

    def serialize(self):
        """
        Returns a representation of the object as a dictionary so
        it can be later exported as JSON. Override this method.

        :return: Dictionary representing the object
        :rtype: dict
        """
        return

    def deserialize(self, obj_dict):
        """
        Re-builds an object from its serialized version.

        :param obj_dict: Dictionary representing a FlatCAMObj
        :type obj_dict: dict
        :return: None
        """
        return

    def add_shape(self, **kwargs):
        if self.deleted:
            raise ObjectDeleted()
        else:
            key = self.shapes.add(tolerance=self.drawing_tolerance, **kwargs)
        return key

    def add_mark_shape(self, **kwargs):
        if self.deleted:
            raise ObjectDeleted()
        else:
            key = self.mark_shapes.add(tolerance=self.drawing_tolerance, **kwargs)
        return key

    @property
    def visible(self):
        return self.shapes.visible

    @visible.setter
    def visible(self, value):
        self.shapes.visible = value

        # Not all object types has annotations
        try:
            self.annotation.visible = value
        except AttributeError:
            pass

    @property
    def drawing_tolerance(self):
        return self._drawing_tolerance if self.units == 'MM' or not self.units else self._drawing_tolerance / 25.4

    @drawing_tolerance.setter
    def drawing_tolerance(self, value):
        self._drawing_tolerance = value if self.units == 'MM' or not self.units else value / 25.4

    def clear(self, update=False):
        self.shapes.clear(update)

        # Not all object types has annotations
        try:
            self.annotation.clear(update)
        except AttributeError:
            pass

    def delete(self):
        # Free resources
        del self.ui
        del self.options

        # Set flag
        self.deleted = True


class FlatCAMGerber(FlatCAMObj, Gerber):
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

        :param grb_list: List of FlatCAMGerber Objects to join.
        :param grb_final: Destination FlatCAMGeometry object.
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
                FlatCAMGerber.merge(grb, grb_final)
            else:   # If not list, just append
                for option in grb.options:
                    if option is not 'name':
                        try:
                            grb_final.options[option] = grb.options[option]
                        except:
                            log.warning("Failed to copy option.", option)

                for geos in grb.solid_geometry:
                    grb_final.solid_geometry.append(geos)
                    grb_final.follow_geometry.append(geos)

                for ap in grb.apertures:
                    if ap not in grb_final.apertures:
                        grb_final.apertures[ap] = grb.apertures[ap]
                    else:
                        if 'solid_geometry' not in grb_final.apertures[ap]:
                            grb_final.apertures[ap]['solid_geometry'] = []
                        for geo in grb.apertures[ap]['solid_geometry']:
                            grb_final.apertures[ap]['solid_geometry'].append(geo)

        grb_final.solid_geometry = MultiPolygon(grb_final.solid_geometry)
        grb_final.follow_geometry = MultiPolygon(grb_final.follow_geometry)

    def __init__(self, name):
        Gerber.__init__(self, steps_per_circle=int(self.app.defaults["gerber_circle_steps"]))
        FlatCAMObj.__init__(self, name)

        self.kind = "gerber"

        # The 'name' is already in self.options from FlatCAMObj
        # Automatically updates the UI
        self.options.update({
            "plot": True,
            "multicolored": False,
            "solid": False,
            "isotooldia": 0.016,
            "isopasses": 1,
            "isooverlap": 0.15,
            "milling_type": "cl",
            "combine_passes": True,
            "noncoppermargin": 0.0,
            "noncopperrounded": False,
            "bboxmargin": 0.0,
            "bboxrounded": False,
            "aperture_display": False,
            "aperture_scale_factor": 1.0,
            "aperture_buffer_factor": 0.0,
            "follow": False
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

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from predecessors.
        self.ser_attrs += ['options', 'kind']

    def set_ui(self, ui):
        """
        Maps options with GUI inputs.
        Connects GUI events to methods.

        :param ui: GUI object.
        :type ui: GerberObjectUI
        :return: None
        """
        FlatCAMObj.set_ui(self, ui)
        FlatCAMApp.App.log.debug("FlatCAMGerber.set_ui()")

        self.replotApertures.connect(self.on_mark_cb_click_table)

        self.form_fields.update({
            "plot": self.ui.plot_cb,
            "multicolored": self.ui.multicolored_cb,
            "solid": self.ui.solid_cb,
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
            "aperture_scale_factor": self.ui.scale_aperture_entry,
            "aperture_buffer_factor": self.ui.buffer_aperture_entry,
            "follow": self.ui.follow_cb
        })

        # Fill form fields only on object create
        self.to_form()

        assert isinstance(self.ui, GerberObjectUI)
        self.ui.plot_cb.stateChanged.connect(self.on_plot_cb_click)
        self.ui.solid_cb.stateChanged.connect(self.on_solid_cb_click)
        self.ui.multicolored_cb.stateChanged.connect(self.on_multicolored_cb_click)
        self.ui.generate_ext_iso_button.clicked.connect(self.on_ext_iso_button_click)
        self.ui.generate_int_iso_button.clicked.connect(self.on_int_iso_button_click)
        self.ui.generate_iso_button.clicked.connect(self.on_iso_button_click)
        self.ui.generate_ncc_button.clicked.connect(self.app.ncclear_tool.run)
        self.ui.generate_cutout_button.clicked.connect(self.app.cutout_tool.run)
        self.ui.generate_bb_button.clicked.connect(self.on_generatebb_button_click)
        self.ui.generate_noncopper_button.clicked.connect(self.on_generatenoncopper_button_click)
        self.ui.aperture_table_visibility_cb.stateChanged.connect(self.on_aperture_table_visibility_change)
        self.ui.follow_cb.stateChanged.connect(self.on_follow_cb_click)
        self.ui.scale_aperture_button.clicked.connect(self.on_scale_aperture_click)
        self.ui.buffer_aperture_button.clicked.connect(self.on_buffer_aperture_click)
        self.ui.new_grb_button.clicked.connect(self.on_new_modified_gerber)

        # Show/Hide Advanced Options
        if self.app.defaults["global_app_level"] == 'b':
            self.ui.level.setText(_(
                '<span style="color:green;"><b>Basic</b></span>'
            ))
            self.ui.apertures_table_label.hide()
            self.ui.aperture_table_visibility_cb.hide()
            self.ui.milling_type_label.hide()
            self.ui.milling_type_radio.hide()
            self.ui.generate_ext_iso_button.hide()
            self.ui.generate_int_iso_button.hide()
            self.ui.follow_cb.hide()
            self.ui.padding_area_label.show()
        else:
            self.ui.level.setText(_(
                '<span style="color:red;"><b>Advanced</b></span>'
            ))
            self.ui.padding_area_label.hide()

        # set initial state of the aperture table and associated widgets
        self.on_aperture_table_visibility_change()

        self.build_ui()

    def build_ui(self):
        FlatCAMObj.build_ui(self)

        try:
            # if connected, disconnect the signal from the slot on item_changed as it creates issues
            self.ui.apertures_table.itemChanged.disconnect()
        except:
            pass

        self.apertures_row = 0
        aper_no = self.apertures_row + 1
        sort = []
        for k, v in list(self.apertures.items()):
            sort.append(int(k))
        sorted_apertures = sorted(sort)

        sort = []
        for k, v in list(self.aperture_macros.items()):
            sort.append(k)
        sorted_macros = sorted(sort)

        n = len(sorted_apertures) + len(sorted_macros)
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
                    '%.4f, %.4f' % (self.apertures[ap_code]['width'] * self.file_units_factor,
                                    self.apertures[ap_code]['height'] * self.file_units_factor
                                    )
                )
                ap_dim_item.setFlags(QtCore.Qt.ItemIsEnabled)
            elif str(self.apertures[ap_code]['type']) == 'P':
                ap_dim_item = QtWidgets.QTableWidgetItem(
                    '%.4f, %.4f' % (self.apertures[ap_code]['diam'] * self.file_units_factor,
                                    self.apertures[ap_code]['nVertices'] * self.file_units_factor)
                )
                ap_dim_item.setFlags(QtCore.Qt.ItemIsEnabled)
            else:
                ap_dim_item = QtWidgets.QTableWidgetItem('')
                ap_dim_item.setFlags(QtCore.Qt.ItemIsEnabled)

            try:
                if self.apertures[ap_code]['size'] is not None:
                    ap_size_item = QtWidgets.QTableWidgetItem('%.4f' %
                                                              float(self.apertures[ap_code]['size'] *
                                                                    self.file_units_factor))
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

            self.ui.apertures_table.setCellWidget(self.apertures_row, 5, mark_item)

            self.apertures_row += 1

        for ap_code in sorted_macros:
            ap_code = str(ap_code)

            ap_id_item = QtWidgets.QTableWidgetItem('%d' % int(self.apertures_row + 1))
            ap_id_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.ui.apertures_table.setItem(self.apertures_row, 0, ap_id_item)  # Tool name/id

            ap_code_item = QtWidgets.QTableWidgetItem(ap_code)

            ap_type_item = QtWidgets.QTableWidgetItem('AM')
            ap_type_item.setFlags(QtCore.Qt.ItemIsEnabled)

            mark_item = FCCheckBox()
            mark_item.setLayoutDirection(QtCore.Qt.RightToLeft)
            # if self.ui.aperture_table_visibility_cb.isChecked():
            #     mark_item.setChecked(True)

            self.ui.apertures_table.setItem(self.apertures_row, 1, ap_code_item)  # Aperture Code
            self.ui.apertures_table.setItem(self.apertures_row, 2, ap_type_item)  # Aperture Type
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
        horizontal_header.resizeSection(0, 20)
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
                self.ui.apertures_table.cellWidget(row, 5).set_value(self.marked_rows[row])

        self.ui_connect()

    def ui_connect(self):
        for row in range(self.ui.apertures_table.rowCount()):
            self.ui.apertures_table.cellWidget(row, 5).clicked.connect(self.on_mark_cb_click_table)

        self.ui.mark_all_cb.clicked.connect(self.on_mark_all_click)

    def ui_disconnect(self):
        for row in range(self.ui.apertures_table.rowCount()):
            try:
                self.ui.apertures_table.cellWidget(row, 5).clicked.disconnect()
            except:
                pass

        try:
            self.ui.mark_all_cb.clicked.disconnect(self.on_mark_all_click)
        except:
            pass

    def on_generatenoncopper_button_click(self, *args):
        self.app.report_usage("gerber_on_generatenoncopper_button")

        self.read_form()
        name = self.options["name"] + "_noncopper"

        def geo_init(geo_obj, app_obj):
            assert isinstance(geo_obj, FlatCAMGeometry)
            bounding_box = self.solid_geometry.envelope.buffer(float(self.options["noncoppermargin"]))
            if not self.options["noncopperrounded"]:
                bounding_box = bounding_box.envelope
            non_copper = bounding_box.difference(self.solid_geometry)
            geo_obj.solid_geometry = non_copper

        # TODO: Check for None
        self.app.new_object("geometry", name, geo_init)

    def on_generatebb_button_click(self, *args):
        self.app.report_usage("gerber_on_generatebb_button")
        self.read_form()
        name = self.options["name"] + "_bbox"

        def geo_init(geo_obj, app_obj):
            assert isinstance(geo_obj, FlatCAMGeometry)
            # Bounding box with rounded corners
            bounding_box = self.solid_geometry.envelope.buffer(float(self.options["bboxmargin"]))
            if not self.options["bboxrounded"]:  # Remove rounded corners
                bounding_box = bounding_box.envelope
            geo_obj.solid_geometry = bounding_box

        self.app.new_object("geometry", name, geo_init)

    def on_ext_iso_button_click(self, *args):

        if self.ui.follow_cb.get_value() == True:
            obj = self.app.collection.get_active()
            obj.follow()
            # in the end toggle the visibility of the origin object so we can see the generated Geometry
            obj.ui.plot_cb.toggle()
        else:
            self.app.report_usage("gerber_on_iso_button")
            self.read_form()
            self.isolate(iso_type=0)

    def on_int_iso_button_click(self, *args):

        if self.ui.follow_cb.get_value() is True:
            obj = self.app.collection.get_active()
            obj.follow()
            # in the end toggle the visibility of the origin object so we can see the generated Geometry
            obj.ui.plot_cb.toggle()
        else:
            self.app.report_usage("gerber_on_iso_button")
            self.read_form()
            self.isolate(iso_type=1)

    def on_iso_button_click(self, *args):

        if self.ui.follow_cb.get_value() is True:
            obj = self.app.collection.get_active()
            obj.follow_geo()
            # in the end toggle the visibility of the origin object so we can see the generated Geometry
            obj.ui.plot_cb.toggle()
        else:
            self.app.report_usage("gerber_on_iso_button")
            self.read_form()
            self.isolate()

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
            follow_obj.options["cnctooldia"] = float(self.options["isotooldia"])
            follow_obj.solid_geometry = self.follow_geometry

        # TODO: Do something if this is None. Offer changing name?
        try:
            self.app.new_object("geometry", follow_name, follow_init)
        except Exception as e:
            return "Operation failed: %s" % str(e)

    def isolate(self, iso_type=None, dia=None, passes=None, overlap=None,
                outname=None, combine=None, milling_type=None, follow=None):
        """
        Creates an isolation routing geometry object in the project.

        :param iso_type: type of isolation to be done: 0 = exteriors, 1 = interiors and 2 = both
        :param dia: Tool diameter
        :param passes: Number of tool widths to cut
        :param overlap: Overlap between passes in fraction of tool diameter
        :param outname: Base name of the output object
        :return: None
        """


        if dia is None:
            dia = float(self.options["isotooldia"])
        if passes is None:
            passes = int(self.options["isopasses"])
        if overlap is None:
            overlap = float(self.options["isooverlap"])
        if combine is None:
            combine = self.options["combine_passes"]
        else:
            combine = bool(combine)
        if milling_type is None:
            milling_type = self.options["milling_type"]
        if iso_type is None:
            self.iso_type = 2
        else:
            self.iso_type = iso_type

        base_name = self.options["name"] + "_iso"
        base_name = outname or base_name

        def generate_envelope(offset, invert, envelope_iso_type=2, follow=None):
            # isolation_geometry produces an envelope that is going on the left of the geometry
            # (the copper features). To leave the least amount of burrs on the features
            # the tool needs to travel on the right side of the features (this is called conventional milling)
            # the first pass is the one cutting all of the features, so it needs to be reversed
            # the other passes overlap preceding ones and cut the left over copper. It is better for them
            # to cut on the right side of the left over copper i.e on the left side of the features.
            try:
                geom = self.isolation_geometry(offset, iso_type=envelope_iso_type, follow=follow)
            except Exception as e:
                log.debug(str(e))
                return 'fail'

            if invert:
                try:
                    if type(geom) is MultiPolygon:
                        pl = []
                        for p in geom:
                            pl.append(Polygon(p.exterior.coords[::-1], p.interiors))
                        geom = MultiPolygon(pl)
                    elif type(geom) is Polygon:
                        geom = Polygon(geom.exterior.coords[::-1], geom.interiors)
                    else:
                        log.debug("FlatCAMGerber.isolate().generate_envelope() Error --> Unexpected Geometry")
                except Exception as e:
                    log.debug("FlatCAMGerber.isolate().generate_envelope() Error --> %s" % str(e))
            return geom

        if combine:

            if self.iso_type == 0:
                iso_name = self.options["name"] + "_ext_iso"
            elif self.iso_type == 1:
                iso_name = self.options["name"] + "_int_iso"
            else:
                iso_name = base_name

            # TODO: This is ugly. Create way to pass data into init function.
            def iso_init(geo_obj, app_obj):
                # Propagate options
                geo_obj.options["cnctooldia"] = float(self.options["isotooldia"])
                geo_obj.solid_geometry = []
                for i in range(passes):
                    iso_offset = (((2 * i + 1) / 2.0) * dia) - (i * overlap * dia)

                    # if milling type is climb then the move is counter-clockwise around features
                    if milling_type == 'cl':
                        # geom = generate_envelope (offset, i == 0)
                        geom = generate_envelope(iso_offset, 1, envelope_iso_type=self.iso_type, follow=follow)
                    else:
                        geom = generate_envelope(iso_offset, 0, envelope_iso_type=self.iso_type, follow=follow)
                    geo_obj.solid_geometry.append(geom)

                # detect if solid_geometry is empty and this require list flattening which is "heavy"
                # or just looking in the lists (they are one level depth) and if any is not empty
                # proceed with object creation, if there are empty and the number of them is the length
                # of the list then we have an empty solid_geometry which should raise a Custom Exception
                empty_cnt = 0
                if not isinstance(geo_obj.solid_geometry, list):
                    geo_obj.solid_geometry = [geo_obj.solid_geometry]

                for g in geo_obj.solid_geometry:
                    if g:
                        app_obj.inform.emit(_(
                            "[success]Isolation geometry created: %s"
                        ) % geo_obj.options["name"])
                        break
                    else:
                        empty_cnt += 1
                if empty_cnt == len(geo_obj.solid_geometry):
                    raise ValidationError("Empty Geometry", None)
                geo_obj.multigeo = False

            # TODO: Do something if this is None. Offer changing name?
            self.app.new_object("geometry", iso_name, iso_init)
        else:
            for i in range(passes):

                offset = (2 * i + 1) / 2.0 * dia - i * overlap * dia
                if passes > 1:
                    if self.iso_type == 0:
                        iso_name = self.options["name"] + "_ext_iso" + str(i + 1)
                    elif self.iso_type == 1:
                        iso_name = self.options["name"] + "_int_iso" + str(i + 1)
                    else:
                        iso_name = base_name + str(i + 1)
                else:
                    if self.iso_type == 0:
                        iso_name = self.options["name"] + "_ext_iso"
                    elif self.iso_type == 1:
                        iso_name = self.options["name"] + "_int_iso"
                    else:
                        iso_name = base_name

                # TODO: This is ugly. Create way to pass data into init function.
                def iso_init(geo_obj, app_obj):
                    # Propagate options
                    geo_obj.options["cnctooldia"] = float(self.options["isotooldia"])

                    # if milling type is climb then the move is counter-clockwise around features
                    if milling_type == 'cl':
                        # geo_obj.solid_geometry = generate_envelope(offset, i == 0)
                        geo_obj.solid_geometry = generate_envelope(offset, 1, envelope_iso_type=self.iso_type,
                                                                   follow=follow)
                    else:
                        geo_obj.solid_geometry = generate_envelope(offset, 0, envelope_iso_type=self.iso_type,
                                                                   follow=follow)

                    # detect if solid_geometry is empty and this require list flattening which is "heavy"
                    # or just looking in the lists (they are one level depth) and if any is not empty
                    # proceed with object creation, if there are empty and the number of them is the length
                    # of the list then we have an empty solid_geometry which should raise a Custom Exception
                    empty_cnt = 0
                    if not isinstance(geo_obj.solid_geometry, list):
                        geo_obj.solid_geometry = [geo_obj.solid_geometry]

                    for g in geo_obj.solid_geometry:
                        if g:
                            app_obj.inform.emit(_(
                                "[success]Isolation geometry created: %s"
                            ) % geo_obj.options["name"])
                            break
                        else:
                            empty_cnt += 1
                    if empty_cnt == len(geo_obj.solid_geometry):
                        raise ValidationError("Empty Geometry", None)
                    geo_obj.multigeo = False

                # TODO: Do something if this is None. Offer changing name?
                self.app.new_object("geometry", iso_name, iso_init)

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
            self.ui.apertures_table.setVisible(True)
            self.ui.scale_aperture_label.setVisible(True)
            self.ui.scale_aperture_entry.setVisible(True)
            self.ui.scale_aperture_button.setVisible(True)

            self.ui.buffer_aperture_label.setVisible(True)
            self.ui.buffer_aperture_entry.setVisible(True)
            self.ui.buffer_aperture_button.setVisible(True)

            self.ui.new_grb_label.setVisible(True)
            self.ui.new_grb_button.setVisible(True)
            self.ui.mark_all_cb.setVisible(True)
            self.ui.mark_all_cb.setChecked(False)
        else:
            self.ui.apertures_table.setVisible(False)
            self.ui.scale_aperture_label.setVisible(False)
            self.ui.scale_aperture_entry.setVisible(False)
            self.ui.scale_aperture_button.setVisible(False)

            self.ui.buffer_aperture_label.setVisible(False)
            self.ui.buffer_aperture_entry.setVisible(False)
            self.ui.buffer_aperture_button.setVisible(False)

            self.ui.new_grb_label.setVisible(False)
            self.ui.new_grb_button.setVisible(False)
            self.ui.mark_all_cb.setVisible(False)

            # on hide disable all mark plots
            for row in range(self.ui.apertures_table.rowCount()):
                self.ui.apertures_table.cellWidget(row, 5).set_value(False)
            self.clear_plot_apertures()

    def on_scale_aperture_click(self, signal):
        try:
            factor = self.ui.scale_aperture_entry.get_value()
        except Exception as e:
            log.debug("FlatCAMGerber.on_scale_aperture_click() --> %s" % str(e))
            self.app.inform.emit(_(
                "[ERROR_NOTCL] The aperture scale factor value is missing or wrong format."
            ))
            return

        def scale_recursion(geom):
            if type(geom) == list or type(geom) is MultiPolygon:
                geoms=list()
                for local_geom in geom:
                    geoms.append(scale_recursion(local_geom))
                return geoms
            else:
                return  affinity.scale(geom, factor, factor, origin='center')

        if not self.ui.apertures_table.selectedItems():
            self.app.inform.emit(_(
                "[WARNING_NOTCL] No aperture to scale. Select at least one aperture and try again."
            ))
            return

        for x in self.ui.apertures_table.selectedItems():
            try:
                apid = self.ui.apertures_table.item(x.row(), 1).text()
            except Exception as e:
                log.debug("FlatCAMGerber.on_scale_aperture_click() --> %s" % str(e))

            self.apertures[apid]['solid_geometry'] = scale_recursion(self.apertures[apid]['solid_geometry'])

        self.on_mark_cb_click_table()

    def on_buffer_aperture_click(self, signal):
        try:
            buff_value = self.ui.buffer_aperture_entry.get_value()
        except Exception as e:
            log.debug("FlatCAMGerber.on_scale_aperture_click() --> %s" % str(e))
            self.app.inform.emit(_(
                "[ERROR_NOTCL] The aperture buffer value is missing or wrong format."
            ))
            return

        def buffer_recursion(geom):
            if type(geom) == list or type(geom) is MultiPolygon:
                geoms=list()
                for local_geom in geom:
                    geoms.append(buffer_recursion(local_geom))
                return geoms
            else:
                return  geom.buffer(buff_value, join_style=2)

        if not self.ui.apertures_table.selectedItems():
            self.app.inform.emit(_(
                "[WARNING_NOTCL] No aperture to scale. Select at least one aperture and try again."
            ))
            return

        for x in self.ui.apertures_table.selectedItems():
            try:
                apid = self.ui.apertures_table.item(x.row(), 1).text()
            except Exception as e:
                log.debug("FlatCAMGerber.on_scale_aperture_click() --> %s" % str(e))

            self.apertures[apid]['solid_geometry'] = buffer_recursion(self.apertures[apid]['solid_geometry'])

        self.on_mark_cb_click_table()

    def on_new_modified_gerber(self, signal):

        name = '%s_ap_mod' % str(self.options['name'])
        apertures = deepcopy(self.apertures)
        options = self.options

        # geometry storage
        poly_buff = []

        # How the object should be initialized
        def obj_init(gerber_obj, app_obj):
            assert isinstance(gerber_obj, FlatCAMGerber), \
                "Expected to initialize a FlatCAMGerber but got %s" % type(gerber_obj)

            gerber_obj.source_file = self.source_file
            gerber_obj.multigeo = False
            gerber_obj.follow = False

            gerber_obj.apertures = apertures
            for option in options:
                # we don't want to overwrite the new name and we don't want to share the 'plot' state
                # because the new object should ve visible even if the source is not visible
                if option != 'name' and option != 'plot':
                    gerber_obj.options[option] = options[option]

            # regenerate solid_geometry
            app_obj.log.debug("Creating new Gerber object. Joining %s polygons.")
            # for ap in apertures:
                # for geo in apertures[ap]['solid_geometry']:
                #     poly_buff.append(geo)
            poly_buff = [geo for ap in apertures for geo in apertures[ap]['solid_geometry']]

            # buffering the poly_buff
            new_geo = MultiPolygon(poly_buff)
            new_geo = new_geo.buffer(0.0000001)
            new_geo = new_geo.buffer(-0.0000001)

            gerber_obj.solid_geometry = new_geo

            app_obj.log.debug("Finished creation of a new Gerber object. Polygons joined.")

        log.debug("on_new_modified_gerber()")

        with self.app.proc_container.new(_("Generating Gerber")) as proc:

            self.app.progress.emit(10)

            ### Object creation ###
            ret = self.app.new_object("gerber", name, obj_init, autoselected=False)
            if ret == 'fail':
                self.app.inform.emit(_(
                    '[ERROR_NOTCL] Cretion of Gerber failed.'
                ))
                return

            self.app.progress.emit(100)

            # GUI feedback
            self.app.inform.emit(_("[success] Created: %s") % name)

    def convert_units(self, units):
        """
        Converts the units of the object by scaling dimensions in all geometry
        and options.

        :param units: Units to which to convert the object: "IN" or "MM".
        :type units: str
        :return: None
        :rtype: None
        """

        factor = Gerber.convert_units(self, units)

        self.options['isotooldia'] = float(self.options['isotooldia']) * factor
        self.options['bboxmargin'] = float(self.options['bboxmargin']) * factor

    def plot(self, **kwargs):
        """

        :param kwargs: color and face_color
        :return:
        """

        FlatCAMApp.App.log.debug(str(inspect.stack()[1][3]) + " --> FlatCAMGerber.plot()")

        # Does all the required setup and returns False
        # if the 'ptint' option is set to False.
        if not FlatCAMObj.plot(self):
            return

        if 'color' in kwargs:
            color = kwargs['color']
        else:
            color = self.app.defaults['global_plot_line']
        if 'face_color' in kwargs:
            face_color = kwargs['face_color']
        else:
            face_color = self.app.defaults['global_plot_fill']

        # if the Follow Geometry checkbox is checked then plot only the follow geometry
        if self.ui.follow_cb.get_value():
            geometry = self.follow_geometry
        else:
            geometry = self.solid_geometry

        # Make sure geometry is iterable.
        try:
            _ = iter(geometry)
        except TypeError:
            geometry = [geometry]

        def random_color():
            color = np.random.rand(4)
            color[3] = 1
            return color

        try:
            if self.options["solid"]:
                for g in geometry:
                    if type(g) == Polygon or type(g) == LineString:
                        self.add_shape(shape=g, color=color,
                                       face_color=random_color() if self.options['multicolored']
                                       else face_color, visible=self.options['plot'])
                    elif type(g) == Point:
                        pass
                    else:
                        for el in g:
                            self.add_shape(shape=el, color=color,
                                           face_color=random_color() if self.options['multicolored']
                                           else face_color, visible=self.options['plot'])
            else:
                for g in geometry:
                    if type(g) == Polygon or type(g) == LineString:
                        self.add_shape(shape=g, color=random_color() if self.options['multicolored'] else 'black',
                                       visible=self.options['plot'])
                    elif type(g) == Point:
                        pass
                    else:
                        for el in g:
                            self.add_shape(shape=el, color=random_color() if self.options['multicolored'] else 'black',
                                           visible=self.options['plot'])
            self.shapes.redraw()
        except (ObjectDeleted, AttributeError):
            self.shapes.clear(update=True)

    # experimental plot() when the solid_geometry is stored in the self.apertures
    def plot_apertures(self, **kwargs):
        """

        :param kwargs: color and face_color
        :return:
        """

        FlatCAMApp.App.log.debug(str(inspect.stack()[1][3]) + " --> FlatCAMGerber.plot_apertures()")

        # Does all the required setup and returns False
        # if the 'ptint' option is set to False.
        if not FlatCAMObj.plot(self):
            return

        # for marking apertures, line color and fill color are the same
        if 'color' in kwargs:
            color = kwargs['color']
        else:
            color = self.app.defaults['global_plot_fill']

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

        with self.app.proc_container.new(_("Plotting Apertures")) as proc:
            self.app.progress.emit(30)

            def job_thread(app_obj):
                self.app.progress.emit(30)

                try:
                    if aperture_to_plot_mark in self.apertures:
                        if type(self.apertures[aperture_to_plot_mark]['solid_geometry']) is not list:
                            self.apertures[aperture_to_plot_mark]['solid_geometry'] = \
                                [self.apertures[aperture_to_plot_mark]['solid_geometry']]
                        for geo in self.apertures[aperture_to_plot_mark]['solid_geometry']:
                            if type(geo) == Polygon or type(geo) == LineString:
                                self.add_mark_shape(shape=geo, color=color, face_color=color, visible=visibility)
                            else:
                                for el in geo:
                                    self.add_mark_shape(shape=el, color=color, face_color=color, visible=visibility)

                    self.mark_shapes.redraw()
                    self.app.progress.emit(100)

                except (ObjectDeleted, AttributeError):
                    self.clear_plot_apertures()

            self.app.worker_task.emit({'fcn': job_thread, 'params': [self]})

    def clear_plot_apertures(self):
        self.mark_shapes.clear(update=True)

    def clear_mark_all(self):
        self.ui.mark_all_cb.set_value(False)
        self.marked_rows[:] = []

    def on_mark_cb_click_table(self):
        self.ui_disconnect()
        # cw = self.sender()
        # cw_index = self.ui.apertures_table.indexAt(cw.pos())
        # cw_row = cw_index.row()
        check_row = 0

        self.clear_plot_apertures()
        self.marked_rows[:] = []

        for row in range(self.ui.apertures_table.rowCount()):
            if self.ui.apertures_table.cellWidget(row, 5).isChecked():
                self.marked_rows.append(True)

                aperture = self.ui.apertures_table.item(row, 1).text()
                # self.plot_apertures(color='#2d4606bf', marked_aperture=aperture, visible=True)
                self.plot_apertures(color='#FD6A02', marked_aperture=aperture, visible=True)
            else:
                self.marked_rows.append(False)

        self.mark_shapes.redraw()

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

    def on_mark_all_click(self, signal):
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
                # self.plot_apertures(color='#2d4606bf', marked_aperture=aperture, visible=True)
                self.plot_apertures(color='#FD6A02', marked_aperture=aperture, visible=True)
        else:
            self.clear_plot_apertures()

        self.ui_connect()

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

    def serialize(self):
        return {
            "options": self.options,
            "kind": self.kind
        }


class FlatCAMExcellon(FlatCAMObj, Excellon):
    """
    Represents Excellon/Drill code.
    """

    ui_type = ExcellonObjectUI
    optionChanged = QtCore.pyqtSignal(str)

    def __init__(self, name):
        Excellon.__init__(self, geo_steps_per_circle=int(self.app.defaults["geometry_circle_steps"]))
        FlatCAMObj.__init__(self, name)

        self.kind = "excellon"

        self.options.update({
            "plot": True,
            "solid": False,
            "drillz": -0.1,
            "travelz": 0.1,
            "feedrate": 5.0,
            "feedrate_rapid": 5.0,
            "tooldia": 0.1,
            "slot_tooldia": 0.1,
            "toolchange": False,
            "toolchangez": 1.0,
            "toolchangexy": "0.0, 0.0",
            "endz": 2.0,
            "startz": None,
            "spindlespeed": None,
            "dwell": True,
            "dwelltime": 1000,
            "ppname_e": 'defaults',
            "z_pdepth": -0.02,
            "feedrate_probe": 3.0,
            "optimization_type": "R",
            "gcode_type": "drills"
        })

        # TODO: Document this.
        self.tool_cbs = {}

        # dict to hold the tool number as key and tool offset as value
        self.tool_offset ={}

        # variable to store the total amount of drills per job
        self.tot_drill_cnt = 0
        self.tool_row = 0

        # variable to store the total amount of slots per job
        self.tot_slot_cnt = 0
        self.tool_row_slots = 0

        # variable to store the distance travelled
        self.travel_distance = 0.0

        # store the source file here
        self.source_file = ""

        self.multigeo = True

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from predecessors.
        self.ser_attrs += ['options', 'kind']

    @staticmethod
    def merge(exc_list, exc_final):
        """
        Merge Excellon objects found in exc_list parameter into exc_final object.
        Options are always copied from source .

        Tools are disregarded, what is taken in consideration is the unique drill diameters found as values in the
        exc_list tools dict's. In the reconstruction section for each unique tool diameter it will be created a
        tool_name to be used in the final Excellon object, exc_final.

        If only one object is in exc_list parameter then this function will copy that object in the exc_final

        :param exc_list: List or one object of FlatCAMExcellon Objects to join.
        :param exc_final: Destination FlatCAMExcellon object.
        :return: None
        """

        # flag to signal that we need to reorder the tools dictionary and drills and slots lists
        flag_order = False

        try:
            flattened_list = list(itertools.chain(*exc_list))
        except TypeError:
            flattened_list = exc_list

        # this dict will hold the unique tool diameters found in the exc_list objects as the dict keys and the dict
        # values will be list of Shapely Points; for drills
        custom_dict_drills = {}

        # this dict will hold the unique tool diameters found in the exc_list objects as the dict keys and the dict
        # values will be list of Shapely Points; for slots
        custom_dict_slots = {}

        for exc in flattened_list:
            # copy options of the current excellon obj to the final excellon obj
            for option in exc.options:
                if option is not 'name':
                    try:
                        exc_final.options[option] = exc.options[option]
                    except:
                        exc.app.log.warning("Failed to copy option.", option)

            for drill in exc.drills:
                exc_tool_dia = float('%.3f' % exc.tools[drill['tool']]['C'])

                if exc_tool_dia not in custom_dict_drills:
                    custom_dict_drills[exc_tool_dia] = [drill['point']]
                else:
                    custom_dict_drills[exc_tool_dia].append(drill['point'])

            for slot in exc.slots:
                exc_tool_dia = float('%.3f' % exc.tools[slot['tool']]['C'])

                if exc_tool_dia not in custom_dict_slots:
                    custom_dict_slots[exc_tool_dia] = [[slot['start'], slot['stop']]]
                else:
                    custom_dict_slots[exc_tool_dia].append([slot['start'], slot['stop']])

            # add the zeros and units to the exc_final object
            exc_final.zeros = exc.zeros
            exc_final.units = exc.units

        # variable to make tool_name for the tools
        current_tool = 0
        # Here we add data to the exc_final object
        # the tools diameter are now the keys in the drill_dia dict and the values are the Shapely Points in case of
        # drills
        for tool_dia in custom_dict_drills:
            # we create a tool name for each key in the drill_dia dict (the key is a unique drill diameter)
            current_tool += 1

            tool_name = str(current_tool)
            spec = {"C": float(tool_dia)}
            exc_final.tools[tool_name] = spec

            # rebuild the drills list of dict's that belong to the exc_final object
            for point in custom_dict_drills[tool_dia]:
                exc_final.drills.append(
                    {
                        "point": point,
                        "tool": str(current_tool)
                    }
                )

        # Here we add data to the exc_final object
        # the tools diameter are now the keys in the drill_dia dict and the values are a list ([start, stop])
        # of two Shapely Points in case of slots
        for tool_dia in custom_dict_slots:
            # we create a tool name for each key in the slot_dia dict (the key is a unique slot diameter)
            # but only if there are no drills
            if not exc_final.tools:
                current_tool += 1
                tool_name = str(current_tool)
                spec = {"C": float(tool_dia)}
                exc_final.tools[tool_name] = spec
            else:
                dia_list = []
                for v in exc_final.tools.values():
                    dia_list.append(float(v["C"]))

                if tool_dia not in dia_list:
                    flag_order = True

                    current_tool = len(dia_list) + 1
                    tool_name = str(current_tool)
                    spec = {"C": float(tool_dia)}
                    exc_final.tools[tool_name] = spec

                else:
                    for k, v in exc_final.tools.items():
                        if v["C"] == tool_dia:
                            current_tool = int(k)
                            break

            # rebuild the slots list of dict's that belong to the exc_final object
            for point in custom_dict_slots[tool_dia]:
                exc_final.slots.append(
                    {
                        "start": point[0],
                        "stop": point[1],
                        "tool": str(current_tool)
                    }
                )

        # flag_order == True means that there was an slot diameter not in the tools and we also have drills
        # and the new tool was added to self.tools therefore we need to reorder the tools and drills and slots
        current_tool = 0
        if flag_order is True:
            dia_list = []
            temp_drills = []
            temp_slots = []
            temp_tools = {}
            for v in exc_final.tools.values():
                dia_list.append(float(v["C"]))
            dia_list.sort()
            for ordered_dia in dia_list:
                current_tool += 1
                tool_name_temp = str(current_tool)
                spec_temp = {"C": float(ordered_dia)}
                temp_tools[tool_name_temp] = spec_temp

                for drill in exc_final.drills:
                    exc_tool_dia = float('%.3f' % exc_final.tools[drill['tool']]['C'])
                    if exc_tool_dia == ordered_dia:
                        temp_drills.append(
                            {
                                "point": drill["point"],
                                "tool": str(current_tool)
                            }
                        )

                for slot in exc_final.slots:
                    slot_tool_dia = float('%.3f' % exc_final.tools[slot['tool']]['C'])
                    if slot_tool_dia == ordered_dia:
                        temp_slots.append(
                            {
                                "start": slot["start"],
                                "stop": slot["stop"],
                                "tool": str(current_tool)
                            }
                        )

            # delete the exc_final tools, drills and slots
            exc_final.tools = dict()
            exc_final.drills[:] = []
            exc_final.slots[:] = []

            # update the exc_final tools, drills and slots with the ordered values
            exc_final.tools = temp_tools
            exc_final.drills[:] = temp_drills
            exc_final.slots[:] = temp_slots

        # create the geometry for the exc_final object
        exc_final.create_geometry()

    def build_ui(self):
        FlatCAMObj.build_ui(self)

        try:
            # if connected, disconnect the signal from the slot on item_changed as it creates issues
            self.ui.tools_table.itemChanged.disconnect()
        except:
            pass

        n = len(self.tools)
        # we have (n+2) rows because there are 'n' tools, each a row, plus the last 2 rows for totals.
        self.ui.tools_table.setRowCount(n + 2)

        self.tot_drill_cnt = 0
        self.tot_slot_cnt = 0

        self.tool_row = 0

        sort = []
        for k, v in list(self.tools.items()):
            sort.append((k, v.get('C')))
        sorted_tools = sorted(sort, key=lambda t1: t1[1])
        tools = [i[0] for i in sorted_tools]

        for tool_no in tools:

            drill_cnt = 0  # variable to store the nr of drills per tool
            slot_cnt = 0  # variable to store the nr of slots per tool

            # Find no of drills for the current tool
            for drill in self.drills:
                if drill['tool'] == tool_no:
                    drill_cnt += 1

            self.tot_drill_cnt += drill_cnt

            # Find no of slots for the current tool
            for slot in self.slots:
                if slot['tool'] == tool_no:
                    slot_cnt += 1

            self.tot_slot_cnt += slot_cnt

            id = QtWidgets.QTableWidgetItem('%d' % int(tool_no))
            id.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.ui.tools_table.setItem(self.tool_row, 0, id)  # Tool name/id

            # Make sure that the drill diameter when in MM is with no more than 2 decimals
            # There are no drill bits in MM with more than 3 decimals diameter
            # For INCH the decimals should be no more than 3. There are no drills under 10mils
            if self.units == 'MM':
                dia = QtWidgets.QTableWidgetItem('%.2f' % (self.tools[tool_no]['C']))
            else:
                dia = QtWidgets.QTableWidgetItem('%.3f' % (self.tools[tool_no]['C']))

            dia.setFlags(QtCore.Qt.ItemIsEnabled)

            drill_count = QtWidgets.QTableWidgetItem('%d' % drill_cnt)
            drill_count.setFlags(QtCore.Qt.ItemIsEnabled)

            # if the slot number is zero is better to not clutter the GUI with zero's so we print a space
            if slot_cnt > 0:
                slot_count = QtWidgets.QTableWidgetItem('%d' % slot_cnt)
            else:
                slot_count = QtWidgets.QTableWidgetItem('')
            slot_count.setFlags(QtCore.Qt.ItemIsEnabled)

            try:
                if self.units == 'MM':
                    t_offset = self.tool_offset[float('%.2f' % float(self.tools[tool_no]['C']))]
                else:
                    t_offset = self.tool_offset[float('%.3f' % float(self.tools[tool_no]['C']))]
            except KeyError:
                    t_offset = self.app.defaults['excellon_offset']
            tool_offset_item = QtWidgets.QTableWidgetItem('%s' % str(t_offset))

            plot_item = FCCheckBox()
            plot_item.setLayoutDirection(QtCore.Qt.RightToLeft)
            if self.ui.plot_cb.isChecked():
                plot_item.setChecked(True)

            self.ui.tools_table.setItem(self.tool_row, 1, dia)  # Diameter
            self.ui.tools_table.setItem(self.tool_row, 2, drill_count)  # Number of drills per tool
            self.ui.tools_table.setItem(self.tool_row, 3, slot_count)  # Number of drills per tool
            self.ui.tools_table.setItem(self.tool_row, 4, tool_offset_item)  # Tool offset
            self.ui.tools_table.setCellWidget(self.tool_row, 5, plot_item)

            self.tool_row += 1

        # add a last row with the Total number of drills
        empty = QtWidgets.QTableWidgetItem('')
        empty.setFlags(~QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        empty_1 = QtWidgets.QTableWidgetItem('')
        empty_1.setFlags(~QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)

        label_tot_drill_count = QtWidgets.QTableWidgetItem(_('Total Drills'))
        tot_drill_count = QtWidgets.QTableWidgetItem('%d' % self.tot_drill_cnt)
        label_tot_drill_count.setFlags(QtCore.Qt.ItemIsEnabled)
        tot_drill_count.setFlags(QtCore.Qt.ItemIsEnabled)

        self.ui.tools_table.setItem(self.tool_row, 0, empty)
        self.ui.tools_table.setItem(self.tool_row, 1, label_tot_drill_count)
        self.ui.tools_table.setItem(self.tool_row, 2, tot_drill_count)  # Total number of drills
        self.ui.tools_table.setItem(self.tool_row, 3, empty_1)  # Total number of drills

        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)

        for k in [1, 2]:
            self.ui.tools_table.item(self.tool_row, k).setForeground(QtGui.QColor(127, 0, 255))
            self.ui.tools_table.item(self.tool_row, k).setFont(font)

        self.tool_row += 1

        # add a last row with the Total number of slots
        empty_2 = QtWidgets.QTableWidgetItem('')
        empty_2.setFlags(~QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        empty_3 = QtWidgets.QTableWidgetItem('')
        empty_3.setFlags(~QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)

        label_tot_slot_count = QtWidgets.QTableWidgetItem(_('Total Slots'))
        tot_slot_count = QtWidgets.QTableWidgetItem('%d' % self.tot_slot_cnt)
        label_tot_slot_count.setFlags(QtCore.Qt.ItemIsEnabled)
        tot_slot_count.setFlags(QtCore.Qt.ItemIsEnabled)

        self.ui.tools_table.setItem(self.tool_row, 0, empty_2)
        self.ui.tools_table.setItem(self.tool_row, 1, label_tot_slot_count)
        self.ui.tools_table.setItem(self.tool_row, 2, empty_3)
        self.ui.tools_table.setItem(self.tool_row, 3, tot_slot_count)  # Total number of slots

        for kl in [1, 2, 3]:
            self.ui.tools_table.item(self.tool_row, kl).setFont(font)
            self.ui.tools_table.item(self.tool_row, kl).setForeground(QtGui.QColor(0, 70, 255))

        # sort the tool diameter column
        # self.ui.tools_table.sortItems(1)
        # all the tools are selected by default
        self.ui.tools_table.selectColumn(0)
        #
        self.ui.tools_table.resizeColumnsToContents()
        self.ui.tools_table.resizeRowsToContents()

        vertical_header = self.ui.tools_table.verticalHeader()
        # vertical_header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        vertical_header.hide()
        self.ui.tools_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        horizontal_header = self.ui.tools_table.horizontalHeader()
        horizontal_header.setMinimumSectionSize(10)
        horizontal_header.setDefaultSectionSize(70)
        horizontal_header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        horizontal_header.resizeSection(0, 20)
        horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        horizontal_header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(5, QtWidgets.QHeaderView.Fixed)
        horizontal_header.resizeSection(5, 17)
        self.ui.tools_table.setColumnWidth(5, 17)

        # horizontal_header.setStretchLastSection(True)




        # horizontal_header.setColumnWidth(2, QtWidgets.QHeaderView.ResizeToContents)

        # horizontal_header.setStretchLastSection(True)
        self.ui.tools_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.ui.tools_table.setSortingEnabled(False)

        self.ui.tools_table.setMinimumHeight(self.ui.tools_table.getHeight())
        self.ui.tools_table.setMaximumHeight(self.ui.tools_table.getHeight())

        if not self.drills:
            self.ui.tdlabel.hide()
            self.ui.tooldia_entry.hide()
            self.ui.generate_milling_button.hide()
        else:
            self.ui.tdlabel.show()
            self.ui.tooldia_entry.show()
            self.ui.generate_milling_button.show()

        if not self.slots:
            self.ui.stdlabel.hide()
            self.ui.slot_tooldia_entry.hide()
            self.ui.generate_milling_slots_button.hide()
        else:
            self.ui.stdlabel.show()
            self.ui.slot_tooldia_entry.show()
            self.ui.generate_milling_slots_button.show()

        # we reactivate the signals after the after the tool adding as we don't need to see the tool been populated
        self.ui.tools_table.itemChanged.connect(self.on_tool_offset_edit)

        self.ui_connect()

    def set_ui(self, ui):
        """
        Configures the user interface for this object.
        Connects options to form fields.

        :param ui: User interface object.
        :type ui: ExcellonObjectUI
        :return: None
        """
        FlatCAMObj.set_ui(self, ui)

        FlatCAMApp.App.log.debug("FlatCAMExcellon.set_ui()")

        self.form_fields.update({
            "plot": self.ui.plot_cb,
            "solid": self.ui.solid_cb,
            "drillz": self.ui.cutz_entry,
            "travelz": self.ui.travelz_entry,
            "feedrate": self.ui.feedrate_entry,
            "feedrate_rapid": self.ui.feedrate_rapid_entry,
            "tooldia": self.ui.tooldia_entry,
            "slot_tooldia": self.ui.slot_tooldia_entry,
            "toolchange": self.ui.toolchange_cb,
            "toolchangez": self.ui.toolchangez_entry,
            "spindlespeed": self.ui.spindlespeed_entry,
            "dwell": self.ui.dwell_cb,
            "dwelltime": self.ui.dwelltime_entry,
            "startz": self.ui.estartz_entry,
            "endz": self.ui.eendz_entry,
            "ppname_e": self.ui.pp_excellon_name_cb,
            "z_pdepth": self.ui.pdepth_entry,
            "feedrate_probe": self.ui.feedrate_probe_entry,
            "gcode_type": self.ui.excellon_gcode_type_radio
        })

        for name in list(self.app.postprocessors.keys()):
            # the HPGL postprocessor is only for Geometry not for Excellon job therefore don't add it
            if name == 'hpgl':
                continue
            self.ui.pp_excellon_name_cb.addItem(name)

        # Fill form fields
        self.to_form()

        # initialize the dict that holds the tools offset
        t_default_offset = self.app.defaults["excellon_offset"]
        if not self.tool_offset:
            for value in self.tools.values():
                if self.units == 'MM':
                    dia = float('%.2f' % float(value['C']))
                else:
                    dia = float('%.3f' % float(value['C']))
                self.tool_offset[dia] = t_default_offset

        # Show/Hide Advanced Options
        if self.app.defaults["global_app_level"] == 'b':
            self.ui.level.setText(_(
                '<span style="color:green;"><b>Basic</b></span>'
            ))

            self.ui.tools_table.setColumnHidden(4, True)
            self.ui.estartz_label.hide()
            self.ui.estartz_entry.hide()
            self.ui.eendz_label.hide()
            self.ui.eendz_entry.hide()
            self.ui.feedrate_rapid_label.hide()
            self.ui.feedrate_rapid_entry.hide()
            self.ui.pdepth_label.hide()
            self.ui.pdepth_entry.hide()
            self.ui.feedrate_probe_label.hide()
            self.ui.feedrate_probe_entry.hide()
        else:
            self.ui.level.setText(_(
                '<span style="color:red;"><b>Advanced</b></span>'
            ))

        assert isinstance(self.ui, ExcellonObjectUI), \
            "Expected a ExcellonObjectUI, got %s" % type(self.ui)
        self.ui.plot_cb.stateChanged.connect(self.on_plot_cb_click)
        self.ui.solid_cb.stateChanged.connect(self.on_solid_cb_click)
        self.ui.generate_cnc_button.clicked.connect(self.on_create_cncjob_button_click)
        self.ui.generate_milling_button.clicked.connect(self.on_generate_milling_button_click)
        self.ui.generate_milling_slots_button.clicked.connect(self.on_generate_milling_slots_button_click)

        self.ui.pp_excellon_name_cb.activated.connect(self.on_pp_changed)

    def ui_connect(self):

        for row in range(self.ui.tools_table.rowCount() - 2):
            self.ui.tools_table.cellWidget(row, 5).clicked.connect(self.on_plot_cb_click_table)
        self.ui.plot_cb.stateChanged.connect(self.on_plot_cb_click)

    def ui_disconnect(self):
        for row in range(self.ui.tools_table.rowCount()):
            try:
                self.ui.tools_table.cellWidget(row, 5).clicked.disconnect()
            except:
                pass

        try:
            self.ui.plot_cb.stateChanged.disconnect()
        except:
            pass

    def on_tool_offset_edit(self):
        # if connected, disconnect the signal from the slot on item_changed as it creates issues
        self.ui.tools_table.itemChanged.disconnect()
        # self.tools_table_exc.selectionModel().currentChanged.disconnect()

        self.is_modified = True

        row_of_item_changed = self.ui.tools_table.currentRow()
        if self.units == 'MM':
            dia = float('%.2f' % float(self.ui.tools_table.item(row_of_item_changed, 1).text()))
        else:
            dia = float('%.3f' % float(self.ui.tools_table.item(row_of_item_changed, 1).text()))

        current_table_offset_edited = None
        if self.ui.tools_table.currentItem() is not None:
            try:
                current_table_offset_edited = float(self.ui.tools_table.currentItem().text())
            except ValueError:
                # try to convert comma to decimal point. if it's still not working error message and return
                try:
                    current_table_offset_edited = float(self.ui.tools_table.currentItem().text().replace(',', '.'))
                    self.ui.tools_table.currentItem().setText(
                        self.ui.tools_table.currentItem().text().replace(',', '.'))
                except ValueError:
                    self.app.inform.emit(_(
                        "[ERROR_NOTCL]Wrong value format entered, use a number."
                    ))
                    self.ui.tools_table.currentItem().setText(str(self.tool_offset[dia]))
                    return

        self.tool_offset[dia] = current_table_offset_edited

        # we reactivate the signals after the after the tool editing
        self.ui.tools_table.itemChanged.connect(self.on_tool_offset_edit)

    def get_selected_tools_list(self):
        """
        Returns the keys to the self.tools dictionary corresponding
        to the selections on the tool list in the GUI.

        :return: List of tools.
        :rtype: list
        """

        return [str(x.text()) for x in self.ui.tools_table.selectedItems()]

    def get_selected_tools_table_items(self):
        """
        Returns a list of lists, each list in the list is made out of row elements

        :return: List of table_tools items.
        :rtype: list
        """
        table_tools_items = []
        for x in self.ui.tools_table.selectedItems():
            # from the columnCount we subtract a value of 1 which represent the last column (plot column)
            # which does not have text
            table_tools_items.append([self.ui.tools_table.item(x.row(), column).text()
                                      for column in range(0, self.ui.tools_table.columnCount() - 1)])
        for item in table_tools_items:
            item[0] = str(item[0])
        return table_tools_items

    def export_excellon(self, whole, fract, e_zeros=None, form='dec', factor=1):
        """
        Returns two values, first is a boolean , if 1 then the file has slots and second contain the Excellon code
        :return: has_slots and Excellon_code
        """

        excellon_code = ''

        # store here if the file has slots, return 1 if any slots, 0 if only drills
        has_slots = 0

        # drills processing
        try:
            if self.drills:
                length = whole + fract
                for tool in self.tools:
                    excellon_code += 'T0%s\n' % str(tool) if int(tool) < 10 else 'T%s\n' % str(tool)

                    for drill in self.drills:
                        if form == 'dec' and tool == drill['tool']:
                            drill_x = drill['point'].x * factor
                            drill_y = drill['point'].y * factor
                            excellon_code += "X{:.{dec}f}Y{:.{dec}f}\n".format(drill_x, drill_y, dec=fract)
                        elif e_zeros == 'LZ' and tool == drill['tool']:
                            drill_x = drill['point'].x * factor
                            drill_y = drill['point'].y * factor

                            exc_x_formatted = "{:.{dec}f}".format(drill_x, dec=fract)
                            exc_y_formatted = "{:.{dec}f}".format(drill_y, dec=fract)

                            # extract whole part and decimal part
                            exc_x_formatted = exc_x_formatted.partition('.')
                            exc_y_formatted = exc_y_formatted.partition('.')

                            # left padd the 'whole' part with zeros
                            x_whole = exc_x_formatted[0].rjust(whole, '0')
                            y_whole = exc_y_formatted[0].rjust(whole, '0')

                            # restore the coordinate padded in the left with 0 and added the decimal part
                            # without the decinal dot
                            exc_x_formatted = x_whole + exc_x_formatted[2]
                            exc_y_formatted = y_whole + exc_y_formatted[2]

                            excellon_code += "X{xform}Y{yform}\n".format(xform=exc_x_formatted,
                                                                         yform=exc_y_formatted)
                        elif tool == drill['tool']:
                            drill_x = drill['point'].x * factor
                            drill_y = drill['point'].y * factor

                            exc_x_formatted = "{:.{dec}f}".format(drill_x, dec=fract).replace('.', '')
                            exc_y_formatted = "{:.{dec}f}".format(drill_y, dec=fract).replace('.', '')

                            # pad with rear zeros
                            exc_x_formatted.ljust(length, '0')
                            exc_y_formatted.ljust(length, '0')

                            excellon_code += "X{xform}Y{yform}\n".format(xform=exc_x_formatted,
                                                                         yform=exc_y_formatted)
        except Exception as e:
            log.debug(str(e))

        # slots processing
        try:
            if self.slots:
                has_slots = 1
                for tool in self.tools:
                    if int(tool) < 10:
                        excellon_code += 'T0' + str(tool) + '\n'
                    else:
                        excellon_code += 'T' + str(tool) + '\n'

                    for slot in self.slots:
                        if form == 'dec' and tool == slot['tool']:
                            start_slot_x = slot['start'].x * factor
                            start_slot_y = slot['start'].y * factor
                            stop_slot_x = slot['stop'].x * factor
                            stop_slot_y = slot['stop'].y * factor

                            excellon_code += "G00X{:.{dec}f}Y{:.{dec}f}\nM15\n".format(start_slot_x,
                                                                                       start_slot_y,
                                                                                       dec=fract)
                            excellon_code += "G00X{:.{dec}f}Y{:.{dec}f}\nM16\n".format(stop_slot_x,
                                                                                       stop_slot_y,
                                                                                       dec=fract)

                        elif e_zeros == 'LZ' and tool == slot['tool']:
                            start_slot_x = slot['start'].x * factor
                            start_slot_y = slot['start'].y * factor
                            stop_slot_x = slot['stop'].x * factor
                            stop_slot_y = slot['stop'].y * factor

                            start_slot_x_formatted = "{:.{dec}f}".format(start_slot_x, dec=fract).replace('.', '')
                            start_slot_y_formatted = "{:.{dec}f}".format(start_slot_y, dec=fract).replace('.', '')
                            stop_slot_x_formatted = "{:.{dec}f}".format(stop_slot_x, dec=fract).replace('.', '')
                            stop_slot_y_formatted = "{:.{dec}f}".format(stop_slot_y, dec=fract).replace('.', '')

                            # extract whole part and decimal part
                            start_slot_x_formatted = start_slot_x_formatted.partition('.')
                            start_slot_y_formatted = start_slot_y_formatted.partition('.')
                            stop_slot_x_formatted = stop_slot_x_formatted.partition('.')
                            stop_slot_y_formatted = stop_slot_y_formatted.partition('.')

                            # left padd the 'whole' part with zeros
                            start_x_whole = start_slot_x_formatted[0].rjust(whole, '0')
                            start_y_whole = start_slot_y_formatted[0].rjust(whole, '0')
                            stop_x_whole = stop_slot_x_formatted[0].rjust(whole, '0')
                            stop_y_whole = stop_slot_y_formatted[0].rjust(whole, '0')

                            # restore the coordinate padded in the left with 0 and added the decimal part
                            # without the decinal dot
                            start_slot_x_formatted = start_x_whole + start_slot_x_formatted[2]
                            start_slot_y_formatted = start_y_whole + start_slot_y_formatted[2]
                            stop_slot_x_formatted = stop_x_whole + stop_slot_x_formatted[2]
                            stop_slot_y_formatted = stop_y_whole + stop_slot_y_formatted[2]

                            excellon_code += "G00X{xstart}Y{ystart}\nM15\n".format(xstart=start_slot_x_formatted,
                                                                                   ystart=start_slot_y_formatted)
                            excellon_code += "G00X{xstop}Y{ystop}\nM16\n".format(xstop=stop_slot_x_formatted,
                                                                                 ystop=stop_slot_y_formatted)
                        elif tool == slot['tool']:
                            start_slot_x = slot['start'].x * factor
                            start_slot_y = slot['start'].y * factor
                            stop_slot_x = slot['stop'].x * factor
                            stop_slot_y = slot['stop'].y * factor
                            length = whole + fract

                            start_slot_x_formatted = "{:.{dec}f}".format(start_slot_x, dec=fract).replace('.', '')
                            start_slot_y_formatted = "{:.{dec}f}".format(start_slot_y, dec=fract).replace('.', '')
                            stop_slot_x_formatted = "{:.{dec}f}".format(stop_slot_x, dec=fract).replace('.', '')
                            stop_slot_y_formatted = "{:.{dec}f}".format(stop_slot_y, dec=fract).replace('.', '')

                            # pad with rear zeros
                            start_slot_x_formatted.ljust(length, '0')
                            start_slot_y_formatted.ljust(length, '0')
                            stop_slot_x_formatted.ljust(length, '0')
                            stop_slot_y_formatted.ljust(length, '0')

                            excellon_code += "G00X{xstart}Y{ystart}\nM15\n".format(xstart=start_slot_x_formatted,
                                                                                   ystart=start_slot_y_formatted)
                            excellon_code += "G00X{xstop}Y{ystop}\nM16\n".format(xstop=stop_slot_x_formatted,
                                                                                 ystop=stop_slot_y_formatted)
        except Exception as e:
            log.debug(str(e))

        if not self.drills and not self.slots:
            log.debug("FlatCAMObj.FlatCAMExcellon.export_excellon() --> Excellon Object is empty: no drills, no slots.")
            return 'fail'

        return has_slots, excellon_code

    def generate_milling_drills(self, tools=None, outname=None, tooldia=None, use_thread=False):
        """
        Note: This method is a good template for generic operations as
        it takes it's options from parameters or otherwise from the
        object's options and returns a (success, msg) tuple as feedback
        for shell operations.

        :return: Success/failure condition tuple (bool, str).
        :rtype: tuple
        """

        # Get the tools from the list. These are keys
        # to self.tools
        if tools is None:
            tools = self.get_selected_tools_list()

        if outname is None:
            outname = self.options["name"] + "_mill"

        if tooldia is None:
            tooldia = float(self.options["tooldia"])

        # Sort tools by diameter. items() -> [('name', diameter), ...]
        # sorted_tools = sorted(list(self.tools.items()), key=lambda tl: tl[1]) # no longer works in Python3

        sort = []
        for k, v in self.tools.items():
            sort.append((k, v.get('C')))
        sorted_tools = sorted(sort, key=lambda t1: t1[1])

        if tools == "all":
            tools = [i[0] for i in sorted_tools]  # List if ordered tool names.
            log.debug("Tools 'all' and sorted are: %s" % str(tools))

        if len(tools) == 0:
            self.app.inform.emit(_(
                "[ERROR_NOTCL]Please select one or more tools from the list and try again."
            ))
            return False, "Error: No tools."

        for tool in tools:
            if tooldia > self.tools[tool]["C"]:
                self.app.inform.emit(_(
                    "[ERROR_NOTCL] Milling tool for DRILLS is larger than hole size. Cancelled."
                ))
                return False, "Error: Milling tool is larger than hole."

        def geo_init(geo_obj, app_obj):
            assert isinstance(geo_obj, FlatCAMGeometry), \
                "Initializer expected a FlatCAMGeometry, got %s" % type(geo_obj)
            app_obj.progress.emit(20)

            ### Add properties to the object

            # get the tool_table items in a list of row items
            tool_table_items = self.get_selected_tools_table_items()
            # insert an information only element in the front
            tool_table_items.insert(0, [_("Tool_nr"), _("Diameter"), _("Drills_Nr"), _("Slots_Nr")])

            geo_obj.options['Tools_in_use'] = tool_table_items
            geo_obj.options['type'] = 'Excellon Geometry'

            geo_obj.solid_geometry = []

            # in case that the tool used has the same diameter with the hole, and since the maximum resolution
            # for FlatCAM is 6 decimals,
            # we add a tenth of the minimum value, meaning 0.0000001, which from our point of view is "almost zero"
            for hole in self.drills:
                if hole['tool'] in tools:
                    buffer_value = self.tools[hole['tool']]["C"] / 2 - tooldia / 2
                    if buffer_value == 0:
                        geo_obj.solid_geometry.append(
                            Point(hole['point']).buffer(0.0000001).exterior)
                    else:
                        geo_obj.solid_geometry.append(
                            Point(hole['point']).buffer(buffer_value).exterior)
        if use_thread:
            def geo_thread(app_obj):
                app_obj.new_object("geometry", outname, geo_init)
                app_obj.progress.emit(100)

            # Create a promise with the new name
            self.app.collection.promise(outname)

            # Send to worker
            self.app.worker_task.emit({'fcn': geo_thread, 'params': [self.app]})
        else:
            self.app.new_object("geometry", outname, geo_init)

        return True, ""

    def generate_milling_slots(self, tools=None, outname=None, tooldia=None, use_thread=False):
        """
        Note: This method is a good template for generic operations as
        it takes it's options from parameters or otherwise from the
        object's options and returns a (success, msg) tuple as feedback
        for shell operations.

        :return: Success/failure condition tuple (bool, str).
        :rtype: tuple
        """

        # Get the tools from the list. These are keys
        # to self.tools
        if tools is None:
            tools = self.get_selected_tools_list()

        if outname is None:
            outname = self.options["name"] + "_mill"

        if tooldia is None:
            tooldia = float(self.options["slot_tooldia"])

        # Sort tools by diameter. items() -> [('name', diameter), ...]
        # sorted_tools = sorted(list(self.tools.items()), key=lambda tl: tl[1]) # no longer works in Python3

        sort = []
        for k, v in self.tools.items():
            sort.append((k, v.get('C')))
        sorted_tools = sorted(sort, key=lambda t1: t1[1])

        if tools == "all":
            tools = [i[0] for i in sorted_tools]  # List if ordered tool names.
            log.debug("Tools 'all' and sorted are: %s" % str(tools))

        if len(tools) == 0:
            self.app.inform.emit(_(
                "[ERROR_NOTCL]Please select one or more tools from the list and try again."
            ))
            return False, "Error: No tools."

        for tool in tools:
            # I add the 0.0001 value to account for the rounding error in converting from IN to MM and reverse
            adj_toolstable_tooldia = float('%.4f' % float(tooldia))
            adj_file_tooldia = float('%.4f' % float(self.tools[tool]["C"]))
            if adj_toolstable_tooldia > adj_file_tooldia + 0.0001:
                self.app.inform.emit(_(
                    "[ERROR_NOTCL] Milling tool for SLOTS is larger than hole size. Cancelled."
                ))
                return False, "Error: Milling tool is larger than hole."

        def geo_init(geo_obj, app_obj):
            assert isinstance(geo_obj, FlatCAMGeometry), \
                "Initializer expected a FlatCAMGeometry, got %s" % type(geo_obj)
            app_obj.progress.emit(20)

            ### Add properties to the object

            # get the tool_table items in a list of row items
            tool_table_items = self.get_selected_tools_table_items()
            # insert an information only element in the front
            tool_table_items.insert(0, [_("Tool_nr"), _("Diameter"), _("Drills_Nr"), _("Slots_Nr")])

            geo_obj.options['Tools_in_use'] = tool_table_items
            geo_obj.options['type'] = 'Excellon Geometry'

            geo_obj.solid_geometry = []

            # in case that the tool used has the same diameter with the hole, and since the maximum resolution
            # for FlatCAM is 6 decimals,
            # we add a tenth of the minimum value, meaning 0.0000001, which from our point of view is "almost zero"
            for slot in self.slots:
                if slot['tool'] in tools:
                    toolstable_tool = float('%.4f' % float(tooldia))
                    file_tool = float('%.4f' % float(self.tools[tool]["C"]))

                    # I add the 0.0001 value to account for the rounding error in converting from IN to MM and reverse
                    # for the file_tool (tooldia actually)
                    buffer_value = float(file_tool / 2) - float(toolstable_tool / 2) + 0.0001
                    if buffer_value == 0:
                        start = slot['start']
                        stop = slot['stop']

                        lines_string = LineString([start, stop])
                        poly = lines_string.buffer(0.0000001, int(self.geo_steps_per_circle)).exterior
                        geo_obj.solid_geometry.append(poly)
                    else:
                        start = slot['start']
                        stop = slot['stop']

                        lines_string = LineString([start, stop])
                        poly = lines_string.buffer(buffer_value, int(self.geo_steps_per_circle)).exterior
                        geo_obj.solid_geometry.append(poly)

        if use_thread:
            def geo_thread(app_obj):
                app_obj.new_object("geometry", outname + '_slot', geo_init)
                app_obj.progress.emit(100)

            # Create a promise with the new name
            self.app.collection.promise(outname)

            # Send to worker
            self.app.worker_task.emit({'fcn': geo_thread, 'params': [self.app]})
        else:
            self.app.new_object("geometry", outname + '_slot', geo_init)

        return True, ""

    def on_generate_milling_button_click(self, *args):
        self.app.report_usage("excellon_on_create_milling_drills button")
        self.read_form()

        self.generate_milling_drills(use_thread=False)

    def on_generate_milling_slots_button_click(self, *args):
        self.app.report_usage("excellon_on_create_milling_slots_button")
        self.read_form()

        self.generate_milling_slots(use_thread=False)

    def on_pp_changed(self):
        current_pp = self.ui.pp_excellon_name_cb.get_value()

        if "toolchange_probe" in current_pp.lower():
            self.ui.pdepth_entry.setVisible(True)
            self.ui.pdepth_label.show()

            self.ui.feedrate_probe_entry.setVisible(True)
            self.ui.feedrate_probe_label.show()
        else:
            self.ui.pdepth_entry.setVisible(False)
            self.ui.pdepth_label.hide()

            self.ui.feedrate_probe_entry.setVisible(False)
            self.ui.feedrate_probe_label.hide()

    def on_create_cncjob_button_click(self, *args):
        self.app.report_usage("excellon_on_create_cncjob_button")
        self.read_form()

        # Get the tools from the list
        tools = self.get_selected_tools_list()

        if len(tools) == 0:
            # if there is a single tool in the table (remember that the last 2 rows are for totals and do not count in
            # tool number) it means that there are 3 rows (1 tool and 2 totals).
            # in this case regardless of the selection status of that tool, use it.
            if self.ui.tools_table.rowCount() == 3:
                tools.append(self.ui.tools_table.item(0, 0).text())
            else:
                self.app.inform.emit(_(
                    "[ERROR_NOTCL]Please select one or more tools from the list and try again."
                ))
                return

        xmin = self.options['xmin']
        ymin = self.options['ymin']
        xmax = self.options['xmax']
        ymax = self.options['ymax']

        job_name = self.options["name"] + "_cnc"
        pp_excellon_name = self.options["ppname_e"]

        # Object initialization function for app.new_object()
        def job_init(job_obj, app_obj):
            assert isinstance(job_obj, FlatCAMCNCjob), \
                "Initializer expected a FlatCAMCNCjob, got %s" % type(job_obj)

            # get the tool_table items in a list of row items
            tool_table_items = self.get_selected_tools_table_items()
            # insert an information only element in the front
            tool_table_items.insert(0, [_("Tool_nr"), _("Diameter"), _("Drills_Nr"), _("Slots_Nr")])

            ### Add properties to the object

            job_obj.options['Tools_in_use'] = tool_table_items
            job_obj.options['type'] = 'Excellon'
            job_obj.options['ppname_e'] = pp_excellon_name

            app_obj.progress.emit(20)
            job_obj.z_cut = float(self.options["drillz"])
            job_obj.tool_offset = self.tool_offset
            job_obj.z_move = float(self.options["travelz"])
            job_obj.feedrate = float(self.options["feedrate"])
            job_obj.feedrate_rapid = float(self.options["feedrate_rapid"])

            job_obj.spindlespeed = float(self.options["spindlespeed"]) if self.options["spindlespeed"] else None
            job_obj.dwell = self.options["dwell"]
            job_obj.dwelltime = float(self.options["dwelltime"])
            job_obj.pp_excellon_name = pp_excellon_name

            job_obj.toolchange_xy_type = "excellon"
            job_obj.coords_decimals = int(self.app.defaults["cncjob_coords_decimals"])
            job_obj.fr_decimals = int(self.app.defaults["cncjob_fr_decimals"])

            job_obj.options['xmin'] = xmin
            job_obj.options['ymin'] = ymin
            job_obj.options['xmax'] = xmax
            job_obj.options['ymax'] = ymax

            try:
                job_obj.z_pdepth = float(self.options["z_pdepth"])
            except ValueError:
                # try to convert comma to decimal point. if it's still not working error message and return
                try:
                    job_obj.z_pdepth = float(self.options["z_pdepth"].replace(',', '.'))
                except ValueError:
                    self.app.inform.emit(
                        _(
                            '[ERROR_NOTCL]Wrong value format for self.defaults["z_pdepth"] or self.options["z_pdepth"]'
                        ))

            try:
                job_obj.feedrate_probe = float(self.options["feedrate_probe"])
            except ValueError:
                # try to convert comma to decimal point. if it's still not working error message and return
                try:
                    job_obj.feedrate_rapid = float(self.options["feedrate_probe"].replace(',', '.'))
                except ValueError:
                    self.app.inform.emit(
                        _(
                            '[ERROR_NOTCL]Wrong value format for self.defaults["feedrate_probe"] '
                            'or self.options["feedrate_probe"]'
                        )
                    )

            # There could be more than one drill size...
            # job_obj.tooldia =   # TODO: duplicate variable!
            # job_obj.options["tooldia"] =

            tools_csv = ','.join(tools)
            ret_val = job_obj.generate_from_excellon_by_tool(self, tools_csv,
                                                             drillz=float(self.options['drillz']),
                                                             toolchange=float(self.options["toolchange"]),
                                                             toolchangexy=self.app.defaults["excellon_toolchangexy"],
                                                             toolchangez=float(self.options["toolchangez"]),
                                                             startz=float(self.options["startz"]) if
                                                             self.options["startz"] else None,
                                                             endz=float(self.options["endz"]),
                                                             excellon_optimization_type=self.app.defaults[
                                                                 "excellon_optimization_type"])
            if ret_val == 'fail':
                return 'fail'
            app_obj.progress.emit(50)
            job_obj.gcode_parse()

            app_obj.progress.emit(60)
            job_obj.create_geometry()

            app_obj.progress.emit(80)

        # To be run in separate thread
        def job_thread(app_obj):
            with self.app.proc_container.new(_("Generating CNC Code")):
                app_obj.new_object("cncjob", job_name, job_init)
                app_obj.progress.emit(100)

        # Create promise for the new name.
        self.app.collection.promise(job_name)

        # Send to worker
        # self.app.worker.add_task(job_thread, [self.app])
        self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})

    def convert_units(self, units):
        factor = Excellon.convert_units(self, units)

        self.options['drillz'] = float(self.options['drillz']) * factor
        self.options['travelz'] = float(self.options['travelz']) * factor
        self.options['feedrate'] = float(self.options['feedrate']) * factor
        self.options['feedrate_rapid'] = float(self.options['feedrate_rapid']) * factor
        self.options['toolchangez'] = float(self.options['toolchangez']) * factor

        if self.app.defaults["excellon_toolchangexy"] == '':
            self.options['toolchangexy'] = "0.0, 0.0"
        else:
            coords_xy = [float(eval(coord)) for coord in self.app.defaults["excellon_toolchangexy"].split(",")]
            if len(coords_xy) < 2:
                self.app.inform.emit(_(
                    "[ERROR]The Toolchange X,Y field in Edit -> Preferences has to be "
                    "in the format (x, y) \nbut now there is only one value, not two. "
                ))
                return 'fail'
            coords_xy[0] *= factor
            coords_xy[1] *= factor
            self.options['toolchangexy'] = "%f, %f" % (coords_xy[0], coords_xy[1])

        if self.options['startz'] is not None:
            self.options['startz'] = float(self.options['startz']) * factor
        self.options['endz'] = float(self.options['endz']) * factor

    def on_solid_cb_click(self, *args):
        if self.muted_ui:
            return
        self.read_form_item('solid')
        self.plot()

    def on_plot_cb_click(self, *args):
        if self.muted_ui:
            return
        self.plot()
        self.read_form_item('plot')

        self.ui_disconnect()
        cb_flag = self.ui.plot_cb.isChecked()
        for row in range(self.ui.tools_table.rowCount() - 2):
            table_cb = self.ui.tools_table.cellWidget(row, 5)
            if cb_flag:
                table_cb.setChecked(True)
            else:
                table_cb.setChecked(False)

        self.ui_connect()

    def on_plot_cb_click_table(self):
        # self.ui.cnc_tools_table.cellWidget(row, 2).widget().setCheckState(QtCore.Qt.Unchecked)
        self.ui_disconnect()
        # cw = self.sender()
        # cw_index = self.ui.tools_table.indexAt(cw.pos())
        # cw_row = cw_index.row()
        check_row = 0

        self.shapes.clear(update=True)
        for tool_key in self.tools:
            solid_geometry = self.tools[tool_key]['solid_geometry']

            # find the geo_tool_table row associated with the tool_key
            for row in range(self.ui.tools_table.rowCount()):
                tool_item = int(self.ui.tools_table.item(row, 0).text())
                if tool_item == int(tool_key):
                    check_row = row
                    break
            if self.ui.tools_table.cellWidget(check_row, 5).isChecked():
                self.options['plot'] = True
                # self.plot_element(element=solid_geometry, visible=True)
                # Plot excellon (All polygons?)
                if self.options["solid"]:
                    for geo in solid_geometry:
                        self.add_shape(shape=geo, color='#750000BF', face_color='#C40000BF',
                                       visible=self.options['plot'],
                                       layer=2)
                else:
                    for geo in solid_geometry:
                        self.add_shape(shape=geo.exterior, color='red', visible=self.options['plot'])
                        for ints in geo.interiors:
                            self.add_shape(shape=ints, color='green', visible=self.options['plot'])
        self.shapes.redraw()

        # make sure that the general plot is disabled if one of the row plot's are disabled and
        # if all the row plot's are enabled also enable the general plot checkbox
        cb_cnt = 0
        total_row = self.ui.tools_table.rowCount()
        for row in range(total_row - 2):
            if self.ui.tools_table.cellWidget(row, 5).isChecked():
                cb_cnt += 1
            else:
                cb_cnt -= 1
        if cb_cnt < total_row - 2:
            self.ui.plot_cb.setChecked(False)
        else:
            self.ui.plot_cb.setChecked(True)
        self.ui_connect()

    # def plot_element(self, element, color='red', visible=None, layer=None):
    #
    #     visible = visible if visible else self.options['plot']
    #
    #     try:
    #         for sub_el in element:
    #             self.plot_element(sub_el)
    #
    #     except TypeError:  # Element is not iterable...
    #         self.add_shape(shape=element, color=color, visible=visible, layer=0)

    def plot(self):

        # Does all the required setup and returns False
        # if the 'ptint' option is set to False.
        if not FlatCAMObj.plot(self):
            return

        try:
            # Plot excellon (All polygons?)
            if self.options["solid"]:
                for tool in self.tools:
                    for geo in self.tools[tool]['solid_geometry']:
                        self.add_shape(shape=geo, color='#750000BF', face_color='#C40000BF',
                                       visible=self.options['plot'],
                                       layer=2)
            else:
                for tool in self.tools:
                    for geo in self.tools[tool]['solid_geometry']:
                        self.add_shape(shape=geo.exterior, color='red', visible=self.options['plot'])
                        for ints in geo.interiors:
                            self.add_shape(shape=ints, color='green', visible=self.options['plot'])

            self.shapes.redraw()
            return
        except (ObjectDeleted, AttributeError, KeyError):
            self.shapes.clear(update=True)

        # this stays for compatibility reasons, in case we try to open old projects
        try:
            _ = iter(self.solid_geometry)
        except TypeError:
            self.solid_geometry = [self.solid_geometry]

        try:
            # Plot excellon (All polygons?)
            if self.options["solid"]:
                for geo in self.solid_geometry:
                    self.add_shape(shape=geo, color='#750000BF', face_color='#C40000BF', visible=self.options['plot'],
                                   layer=2)
            else:
                for geo in self.solid_geometry:
                    self.add_shape(shape=geo.exterior, color='red', visible=self.options['plot'])
                    for ints in geo.interiors:
                        self.add_shape(shape=ints, color='green', visible=self.options['plot'])

            self.shapes.redraw()
        except (ObjectDeleted, AttributeError):
            self.shapes.clear(update=True)

        # try:
        #     # Plot excellon (All polygons?)
        #     if self.options["solid"]:
        #         for geo_type in self.solid_geometry:
        #             if geo_type is not None:
        #                 if type(geo_type) is dict:
        #                     for tooldia in geo_type:
        #                         geo_list = geo_type[tooldia]
        #                         for geo in geo_list:
        #                             self.add_shape(shape=geo, color='#750000BF', face_color='#C40000BF',
        #                                            visible=self.options['plot'],
        #                                            layer=2)
        #                 else:
        #                     self.add_shape(shape=geo_type, color='#750000BF', face_color='#C40000BF',
        #                                    visible=self.options['plot'],
        #                                    layer=2)
        #     else:
        #         for geo_type in self.solid_geometry:
        #             if geo_type is not None:
        #                 if type(geo_type) is dict:
        #                     for tooldia in geo_type:
        #                         geo_list = geo_type[tooldia]
        #                         for geo in geo_list:
        #                             self.add_shape(shape=geo.exterior, color='red', visible=self.options['plot'])
        #                             for ints in geo.interiors:
        #                                 self.add_shape(shape=ints, color='green', visible=self.options['plot'])
        #                 else:
        #                     self.add_shape(shape=geo_type.exterior, color='red', visible=self.options['plot'])
        #                     for ints in geo_type.interiors:
        #                         self.add_shape(shape=ints, color='green', visible=self.options['plot'])
        #     self.shapes.redraw()
        # except (ObjectDeleted, AttributeError):
        #     self.shapes.clear(update=True)


class FlatCAMGeometry(FlatCAMObj, Geometry):
    """
    Geometric object not associated with a specific
    format.
    """
    optionChanged = QtCore.pyqtSignal(str)
    ui_type = GeometryObjectUI

    @staticmethod
    def merge(geo_list, geo_final, multigeo=None):
        """
        Merges the geometry of objects in grb_list into
        the geometry of geo_final.

        :param geo_list: List of FlatCAMGerber Objects to join.
        :param geo_final: Destination FlatCAMGerber object.
        :return: None
        """

        if geo_final.solid_geometry is None:
            geo_final.solid_geometry = []

        if type(geo_final.solid_geometry) is not list:
            geo_final.solid_geometry = [geo_final.solid_geometry]



        for geo in geo_list:
            for option in geo.options:
                if option is not 'name':
                    try:
                        geo_final.options[option] = geo.options[option]
                    except:
                        log.warning("Failed to copy option.", option)

            # Expand lists
            if type(geo) is list:
                FlatCAMGeometry.merge(geo, geo_final)
            # If not list, just append
            else:
                # merge solid_geometry, useful for singletool geometry, for multitool each is empty
                if multigeo is None or multigeo == False:
                    geo_final.multigeo = False
                    try:
                        geo_final.solid_geometry.append(geo.solid_geometry)
                    except Exception as e:
                        log.debug("FlatCAMGeometry.merge() --> %s" % str(e))
                else:
                    geo_final.multigeo = True
                    # if multigeo the solid_geometry is empty in the object attributes because it now lives in the
                    # tools object attribute, as a key value
                    geo_final.solid_geometry = []

                # find the tool_uid maximum value in the geo_final
                geo_final_uid_list = []
                for key in geo_final.tools:
                    geo_final_uid_list.append(int(key))
                try:
                    max_uid = max(geo_final_uid_list, key=int)
                except ValueError:
                    max_uid = 0

                # add and merge tools. If what we try to merge as Geometry is Excellon's and/or Gerber's then don't try
                # to merge the obj.tools as it is likely there is none to merge.
                if not isinstance(geo, FlatCAMGerber) and not isinstance(geo, FlatCAMExcellon):
                    for tool_uid in geo.tools:
                        max_uid += 1
                        geo_final.tools[max_uid] = deepcopy(geo.tools[tool_uid])

    @staticmethod
    def get_pts(o):
        """
        Returns a list of all points in the object, where
        the object can be a MultiPolygon, Polygon, Not a polygon, or a list
        of such. Search is done recursively.

        :param: geometric object
        :return: List of points
        :rtype: list
        """
        pts = []

        ## Iterable: descend into each item.
        try:
            for subo in o:
                pts += FlatCAMGeometry.get_pts(subo)

        ## Non-iterable
        except TypeError:
            if o is not None:
                if type(o) == MultiPolygon:
                    for poly in o:
                        pts += FlatCAMGeometry.get_pts(poly)
                ## Descend into .exerior and .interiors
                elif type(o) == Polygon:
                    pts += FlatCAMGeometry.get_pts(o.exterior)
                    for i in o.interiors:
                        pts += FlatCAMGeometry.get_pts(i)
                elif type(o) == MultiLineString:
                    for line in o:
                        pts += FlatCAMGeometry.get_pts(line)
                ## Has .coords: list them.
                else:
                    pts += list(o.coords)
            else:
                return
        return pts

    def __init__(self, name):
        FlatCAMObj.__init__(self, name)
        Geometry.__init__(self, geo_steps_per_circle=int(self.app.defaults["geometry_circle_steps"]))

        self.kind = "geometry"

        self.options.update({
            "plot": True,
            "cutz": -0.002,
            "vtipdia": 0.1,
            "vtipangle": 30,
            "travelz": 0.1,
            "feedrate": 5.0,
            "feedrate_z": 5.0,
            "feedrate_rapid": 5.0,
            "spindlespeed": None,
            "dwell": True,
            "dwelltime": 1000,
            "multidepth": False,
            "depthperpass": 0.002,
            "extracut": False,
            "endz": 2.0,
            "toolchange": False,
            "toolchangez": 1.0,
            "toolchangexy": "0.0, 0.0",
            "startz": None,
            "ppname_g": 'default',
            "z_pdepth": -0.02,
            "feedrate_probe": 3.0,
        })

        if "cnctooldia" not in self.options:
            self.options["cnctooldia"] =  self.app.defaults["geometry_cnctooldia"]

        self.options["startz"] = self.app.defaults["geometry_startz"]

        # this will hold the tool unique ID that is useful when having multiple tools with same diameter
        self.tooluid = 0

        '''
            self.tools = {}
            This is a dictionary. Each dict key is associated with a tool used in geo_tools_table. The key is the 
            tool_id of the tools and the value is another dict that will hold the data under the following form:
                {tooluid:   {
                            'tooldia': 1,
                            'offset': 'Path',
                            'offset_value': 0.0
                            'type': 'Rough',
                            'tool_type': 'C1',
                            'data': self.default_tool_data
                            'solid_geometry': []
                            }
                }
        '''
        self.tools = {}

        # this dict is to store those elements (tools) of self.tools that are selected in the self.geo_tools_table
        # those elements are the ones used for generating GCode
        self.sel_tools = {}

        self.offset_item_options = [_("Path"), _("In"), _("Out"), _("Custom")]
        self.type_item_options = [_("Iso"), _("Rough"), _("Finish")]
        self.tool_type_item_options = ["C1", "C2", "C3", "C4", "B", "V"]

        # flag to store if the V-Shape tool is selected in self.ui.geo_tools_table
        self.v_tool_type = None

        # flag to store if the Geometry is type 'multi-geometry' meaning that each tool has it's own geometry
        # the default value is False
        self.multigeo = False

        # flag to store if the geometry is part of a special group of geometries that can't be processed by the default
        # engine of FlatCAM. Most likely are generated by some of tools and are special cases of geometries.
        self. special_group = None

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from predecessors.
        self.ser_attrs += ['options', 'kind', 'tools', 'multigeo']

    def build_ui(self):

        self.ui_disconnect()

        FlatCAMObj.build_ui(self)

        offset = 0
        tool_idx = 0

        n = len(self.tools)
        self.ui.geo_tools_table.setRowCount(n)

        for tooluid_key, tooluid_value in self.tools.items():
            tool_idx += 1
            row_no = tool_idx - 1

            id = QtWidgets.QTableWidgetItem('%d' % int(tool_idx))
            id.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.ui.geo_tools_table.setItem(row_no, 0, id)  # Tool name/id

            # Make sure that the tool diameter when in MM is with no more than 2 decimals.
            # There are no tool bits in MM with more than 3 decimals diameter.
            # For INCH the decimals should be no more than 3. There are no tools under 10mils.
            if self.units == 'MM':
                dia_item = QtWidgets.QTableWidgetItem('%.2f' % float(tooluid_value['tooldia']))
            else:
                dia_item = QtWidgets.QTableWidgetItem('%.4f' % float(tooluid_value['tooldia']))

            dia_item.setFlags(QtCore.Qt.ItemIsEnabled)

            offset_item = QtWidgets.QComboBox()
            for item in self.offset_item_options:
                offset_item.addItem(item)
            offset_item.setStyleSheet('background-color: rgb(255,255,255)')
            idx = offset_item.findText(tooluid_value['offset'])
            offset_item.setCurrentIndex(idx)

            type_item = QtWidgets.QComboBox()
            for item in self.type_item_options:
                type_item.addItem(item)
            type_item.setStyleSheet('background-color: rgb(255,255,255)')
            idx = type_item.findText(tooluid_value['type'])
            type_item.setCurrentIndex(idx)

            tool_type_item = QtWidgets.QComboBox()
            for item in self.tool_type_item_options:
                tool_type_item.addItem(item)
                tool_type_item.setStyleSheet('background-color: rgb(255,255,255)')
            idx = tool_type_item.findText(tooluid_value['tool_type'])
            tool_type_item.setCurrentIndex(idx)

            tool_uid_item = QtWidgets.QTableWidgetItem(str(tooluid_key))

            plot_item = FCCheckBox()
            plot_item.setLayoutDirection(QtCore.Qt.RightToLeft)
            if self.ui.plot_cb.isChecked():
                plot_item.setChecked(True)

            self.ui.geo_tools_table.setItem(row_no, 1, dia_item)  # Diameter
            self.ui.geo_tools_table.setCellWidget(row_no, 2, offset_item)
            self.ui.geo_tools_table.setCellWidget(row_no, 3, type_item)
            self.ui.geo_tools_table.setCellWidget(row_no, 4, tool_type_item)

            ### REMEMBER: THIS COLUMN IS HIDDEN IN OBJECTUI.PY ###
            self.ui.geo_tools_table.setItem(row_no, 5, tool_uid_item)  # Tool unique ID
            self.ui.geo_tools_table.setCellWidget(row_no, 6, plot_item)

            try:
                self.ui.tool_offset_entry.set_value(tooluid_value['offset_value'])
            except:
                log.debug("build_ui() --> Could not set the 'offset_value' key in self.tools")

        # make the diameter column editable
        for row in range(tool_idx):
            self.ui.geo_tools_table.item(row, 1).setFlags(QtCore.Qt.ItemIsSelectable |
                                                          QtCore.Qt.ItemIsEditable |
                                                          QtCore.Qt.ItemIsEnabled)

        # sort the tool diameter column
        # self.ui.geo_tools_table.sortItems(1)
        # all the tools are selected by default
        # self.ui.geo_tools_table.selectColumn(0)

        self.ui.geo_tools_table.resizeColumnsToContents()
        self.ui.geo_tools_table.resizeRowsToContents()

        vertical_header = self.ui.geo_tools_table.verticalHeader()
        # vertical_header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        vertical_header.hide()
        self.ui.geo_tools_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        horizontal_header = self.ui.geo_tools_table.horizontalHeader()
        horizontal_header.setMinimumSectionSize(10)
        horizontal_header.setDefaultSectionSize(70)
        horizontal_header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        horizontal_header.resizeSection(0, 20)
        horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        # horizontal_header.setColumnWidth(2, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(4, QtWidgets.QHeaderView.Fixed)
        horizontal_header.resizeSection(4, 40)
        horizontal_header.setSectionResizeMode(6, QtWidgets.QHeaderView.Fixed)
        horizontal_header.resizeSection(4, 17)
        # horizontal_header.setStretchLastSection(True)
        self.ui.geo_tools_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.ui.geo_tools_table.setColumnWidth(0, 20)
        self.ui.geo_tools_table.setColumnWidth(4, 40)
        self.ui.geo_tools_table.setColumnWidth(6, 17)

        # self.ui.geo_tools_table.setSortingEnabled(True)

        self.ui.geo_tools_table.setMinimumHeight(self.ui.geo_tools_table.getHeight())
        self.ui.geo_tools_table.setMaximumHeight(self.ui.geo_tools_table.getHeight())

        # update UI for all rows - useful after units conversion but only if there is at least one row
        row_cnt = self.ui.geo_tools_table.rowCount()
        if row_cnt > 0:
            for r in range(row_cnt):
                self.update_ui(r)

        # select only the first tool / row
        selected_row = 0
        try:
            self.select_tools_table_row(selected_row, clearsel=True)
            # update the Geometry UI
            self.update_ui()
        except Exception as e:
            # when the tools table is empty there will be this error but once the table is populated it will go away
            log.debug(str(e))

        # disable the Plot column in Tool Table if the geometry is SingleGeo as it is not needed
        # and can create some problems
        if self.multigeo is False:
            self.ui.geo_tools_table.setColumnHidden(6, True)
        else:
            self.ui.geo_tools_table.setColumnHidden(6, False)

        self.set_tool_offset_visibility(selected_row)
        self.ui_connect()

    def set_ui(self, ui):
        FlatCAMObj.set_ui(self, ui)

        log.debug("FlatCAMGeometry.set_ui()")

        assert isinstance(self.ui, GeometryObjectUI), \
            "Expected a GeometryObjectUI, got %s" % type(self.ui)

        # populate postprocessor names in the combobox
        for name in list(self.app.postprocessors.keys()):
            self.ui.pp_geometry_name_cb.addItem(name)

        self.form_fields.update({
            "plot": self.ui.plot_cb,
            "cutz": self.ui.cutz_entry,
            "vtipdia": self.ui.tipdia_entry,
            "vtipangle": self.ui.tipangle_entry,
            "travelz": self.ui.travelz_entry,
            "feedrate": self.ui.cncfeedrate_entry,
            "feedrate_z": self.ui.cncplunge_entry,
            "feedrate_rapid": self.ui.cncfeedrate_rapid_entry,
            "spindlespeed": self.ui.cncspindlespeed_entry,
            "dwell": self.ui.dwell_cb,
            "dwelltime": self.ui.dwelltime_entry,
            "multidepth": self.ui.mpass_cb,
            "ppname_g": self.ui.pp_geometry_name_cb,
            "z_pdepth": self.ui.pdepth_entry,
            "feedrate_probe": self.ui.feedrate_probe_entry,
            "depthperpass": self.ui.maxdepth_entry,
            "extracut": self.ui.extracut_cb,
            "toolchange": self.ui.toolchangeg_cb,
            "toolchangez": self.ui.toolchangez_entry,
            "endz": self.ui.gendz_entry,
        })

        # Fill form fields only on object create
        self.to_form()

        self.ui.tipdialabel.hide()
        self.ui.tipdia_entry.hide()
        self.ui.tipanglelabel.hide()
        self.ui.tipangle_entry.hide()
        self.ui.cutz_entry.setDisabled(False)

        # store here the default data for Geometry Data
        self.default_data = {}
        self.default_data.update({
            "name": None,
            "plot": None,
            "cutz": None,
            "vtipdia": None,
            "vtipangle": None,
            "travelz": None,
            "feedrate": None,
            "feedrate_z": None,
            "feedrate_rapid": None,
            "dwell": None,
            "dwelltime": None,
            "multidepth": None,
            "ppname_g": None,
            "depthperpass": None,
            "extracut": None,
            "toolchange": None,
            "toolchangez": None,
            "endz": None,
            "spindlespeed": None,
            "toolchangexy": None,
            "startz": None
        })

        # fill in self.default_data values from self.options
        for def_key in self.default_data:
            for opt_key, opt_val in self.options.items():
                if def_key == opt_key:
                    self.default_data[def_key] = opt_val

        self.tooluid += 1
        if not self.tools:
            self.tools.update({
                self.tooluid: {
                    'tooldia': float(self.options["cnctooldia"]),
                    'offset': _('Path'),
                    'offset_value': 0.0,
                    'type': _('Rough'),
                    'tool_type': 'C1',
                    'data': self.default_data,
                    'solid_geometry': self.solid_geometry
                }
            })
        else:
            # if self.tools is not empty then it can safely be assumed that it comes from an opened project.
            # Because of the serialization the self.tools list on project save, the dict keys (members of self.tools
            # are each a dict) are turned into strings so we rebuild the self.tools elements so the keys are
            # again float type; dict's don't like having keys changed when iterated through therefore the need for the
            # following convoluted way of changing the keys from string to float type
            temp_tools = {}
            new_key = 0.0
            for tooluid_key in self.tools:
                val = deepcopy(self.tools[tooluid_key])
                new_key = deepcopy(int(tooluid_key))
                temp_tools[new_key] = val

            self.tools.clear()
            self.tools = deepcopy(temp_tools)

        self.ui.tool_offset_entry.hide()
        self.ui.tool_offset_lbl.hide()

        # used to store the state of the mpass_cb if the selected postproc for geometry is hpgl
        self.old_pp_state = self.default_data['multidepth']
        self.old_toolchangeg_state = self.default_data['toolchange']

        if not isinstance(self.ui, GeometryObjectUI):
            log.debug("Expected a GeometryObjectUI, got %s" % type(self.ui))
            return

        self.ui.geo_tools_table.setupContextMenu()
        self.ui.geo_tools_table.addContextMenu(
            _("Copy"), self.on_tool_copy, icon=QtGui.QIcon("share/copy16.png"))
        self.ui.geo_tools_table.addContextMenu(
            _("Delete"), lambda: self.on_tool_delete(all=None), icon=QtGui.QIcon("share/delete32.png"))

        # Show/Hide Advanced Options
        if self.app.defaults["global_app_level"] == 'b':
            self.ui.level.setText(_(
                '<span style="color:green;"><b>Basic</b></span>'
            ))

            self.ui.geo_tools_table.setColumnHidden(2, True)
            self.ui.geo_tools_table.setColumnHidden(3, True)
            self.ui.geo_tools_table.setColumnHidden(4, True)
            self.ui.addtool_entry_lbl.hide()
            self.ui.addtool_entry.hide()
            self.ui.addtool_btn.hide()
            self.ui.copytool_btn.hide()
            self.ui.deltool_btn.hide()
            self.ui.endzlabel.hide()
            self.ui.gendz_entry.hide()
            self.ui.fr_rapidlabel.hide()
            self.ui.cncfeedrate_rapid_entry.hide()
            self.ui.extracut_cb.hide()
            self.ui.pdepth_label.hide()
            self.ui.pdepth_entry.hide()
            self.ui.feedrate_probe_label.hide()
            self.ui.feedrate_probe_entry.hide()
        else:
            self.ui.level.setText(_(
                '<span style="color:red;"><b>Advanced</b></span>'
            ))

        self.ui.plot_cb.stateChanged.connect(self.on_plot_cb_click)
        self.ui.generate_cnc_button.clicked.connect(self.on_generatecnc_button_click)
        self.ui.paint_tool_button.clicked.connect(lambda: self.app.paint_tool.run(toggle=False))
        self.ui.pp_geometry_name_cb.activated.connect(self.on_pp_changed)

    def set_tool_offset_visibility(self, current_row):
        if current_row is None:
            return
        try:
            tool_offset = self.ui.geo_tools_table.cellWidget(current_row, 2)
            if tool_offset is not None:
                tool_offset_txt = tool_offset.currentText()
                if tool_offset_txt == _('Custom'):
                    self.ui.tool_offset_entry.show()
                    self.ui.tool_offset_lbl.show()
                else:
                    self.ui.tool_offset_entry.hide()
                    self.ui.tool_offset_lbl.hide()
        except Exception as e:
            log.debug("set_tool_offset_visibility() --> " + str(e))
            return

    def on_offset_value_edited(self):
        '''
        This will save the offset_value into self.tools storage whenever the oofset value is edited
        :return:
        '''
        for current_row in self.ui.geo_tools_table.selectedItems():
            # sometime the header get selected and it has row number -1
            # we don't want to do anything with the header :)
            if current_row.row() < 0:
                continue
            tool_uid = int(self.ui.geo_tools_table.item(current_row.row(), 5).text())
            self.set_tool_offset_visibility(current_row.row())

            for tooluid_key, tooluid_value in self.tools.items():
                if int(tooluid_key) == tool_uid:
                    try:
                        tooluid_value['offset_value'] = float(self.ui.tool_offset_entry.get_value())
                    except ValueError:
                        # try to convert comma to decimal point. if it's still not working error message and return
                        try:
                            tooluid_value['offset_value'] = float(
                                self.ui.tool_offset_entry.get_value().replace(',', '.')
                            )
                        except ValueError:
                            self.app.inform.emit(_(
                                "[ERROR_NOTCL]Wrong value format entered, "
                                "use a number."
                            )
                            )
                            return

    def ui_connect(self):

        # on any change to the widgets that matter it will be called self.gui_form_to_storage which will save the
        # changes in geometry UI
        for i in range(self.ui.grid3.count()):
            try:
                # works for CheckBoxes
                self.ui.grid3.itemAt(i).widget().stateChanged.connect(self.gui_form_to_storage)
            except:
                # works for ComboBoxes
                try:
                    self.ui.grid3.itemAt(i).widget().currentIndexChanged.connect(self.gui_form_to_storage)
                except:
                    # works for Entry
                    try:
                        self.ui.grid3.itemAt(i).widget().editingFinished.connect(self.gui_form_to_storage)
                    except:
                        pass

        for row in range(self.ui.geo_tools_table.rowCount()):
            for col in [2, 3, 4]:
                self.ui.geo_tools_table.cellWidget(row, col).currentIndexChanged.connect(
                    self.on_tooltable_cellwidget_change)

        # I use lambda's because the connected functions have parameters that could be used in certain scenarios
        self.ui.addtool_btn.clicked.connect(lambda: self.on_tool_add())
        self.ui.copytool_btn.clicked.connect(lambda: self.on_tool_copy())
        self.ui.deltool_btn.clicked.connect(lambda: self.on_tool_delete())

        self.ui.geo_tools_table.currentItemChanged.connect(self.on_row_selection_change)
        self.ui.geo_tools_table.itemChanged.connect(self.on_tool_edit)
        self.ui.tool_offset_entry.editingFinished.connect(self.on_offset_value_edited)

        for row in range(self.ui.geo_tools_table.rowCount()):
            self.ui.geo_tools_table.cellWidget(row, 6).clicked.connect(self.on_plot_cb_click_table)
        self.ui.plot_cb.stateChanged.connect(self.on_plot_cb_click)

    def ui_disconnect(self):

        try:
            # on any change to the widgets that matter it will be called self.gui_form_to_storage which will save the
            # changes in geometry UI
            for i in range(self.ui.grid3.count()):
                if isinstance(self.ui.grid3.itemAt(i).widget(), FCCheckBox):
                    self.ui.grid3.itemAt(i).widget().stateChanged.disconnect()

                if isinstance(self.ui.grid3.itemAt(i).widget(), FCComboBox):
                    self.ui.grid3.itemAt(i).widget().currentIndexChanged.disconnect()

                if isinstance(self.ui.grid3.itemAt(i).widget(), LengthEntry) or \
                        isinstance(self.ui.grid3.itemAt(i).widget(), IntEntry) or \
                        isinstance(self.ui.grid3.itemAt(i).widget(), FCEntry):
                    self.ui.grid3.itemAt(i).widget().editingFinished.disconnect()
        except:
            pass

        try:
            for row in range(self.ui.geo_tools_table.rowCount()):
                for col in [2, 3, 4]:
                    self.ui.geo_tools_table.cellWidget(row, col).currentIndexChanged.disconnect()
        except:
            pass

        # I use lambda's because the connected functions have parameters that could be used in certain scenarios
        try:
            self.ui.addtool_btn.clicked.disconnect()
        except:
            pass

        try:
            self.ui.copytool_btn.clicked.disconnect()
        except:
            pass

        try:
            self.ui.deltool_btn.clicked.disconnect()
        except:
            pass

        try:
            self.ui.geo_tools_table.currentItemChanged.disconnect()
        except:
            pass

        try:
            self.ui.geo_tools_table.itemChanged.disconnect()
        except:
            pass

        try:
            self.ui.tool_offset_entry.editingFinished.disconnect()
        except:
            pass

        for row in range(self.ui.geo_tools_table.rowCount()):
            try:
                self.ui.geo_tools_table.cellWidget(row, 6).clicked.disconnect()
            except:
                pass

        try:
            self.ui.plot_cb.stateChanged.disconnect()
        except:
            pass

    def on_tool_add(self, dia=None):
        self.ui_disconnect()

        last_offset = None
        last_offset_value = None
        last_type = None
        last_tool_type = None
        last_data = None
        last_solid_geometry = []

        # if a Tool diameter entered is a char instead a number the final message of Tool adding is changed
        # because the Default value for Tool is used.
        change_message = False

        if dia is not None:
            tooldia = dia
        else:
            try:
                tooldia = float(self.ui.addtool_entry.get_value())
            except ValueError:
                # try to convert comma to decimal point. if it's still not working error message and return
                try:
                    tooldia = float(self.ui.addtool_entry.get_value().replace(',', '.'))
                except ValueError:
                    change_message = True
                    tooldia = float(self.app.defaults["geometry_cnctooldia"])

            if tooldia is None:
                self.build_ui()
                self.app.inform.emit(_(
                    "[ERROR_NOTCL] Please enter the desired tool diameter in Float format."
                ))
                return

        # construct a list of all 'tooluid' in the self.tools
        tool_uid_list = []
        for tooluid_key in self.tools:
            tool_uid_item = int(tooluid_key)
            tool_uid_list.append(tool_uid_item)

        # find maximum from the temp_uid, add 1 and this is the new 'tooluid'
        if not tool_uid_list:
            max_uid = 0
        else:
            max_uid = max(tool_uid_list)
        self.tooluid = max_uid + 1

        if self.units == 'IN':
            tooldia = float('%.4f' % tooldia)
        else:
            tooldia = float('%.2f' % tooldia)

        # here we actually add the new tool; if there is no tool in the tool table we add a tool with default data
        # otherwise we add a tool with data copied from last tool
        if not self.tools:
            self.tools.update({
                self.tooluid: {
                    'tooldia': tooldia,
                    'offset': _('Path'),
                    'offset_value': 0.0,
                    'type': _('Rough'),
                    'tool_type': 'C1',
                    'data': deepcopy(self.default_data),
                    'solid_geometry': self.solid_geometry
                }
            })
        else:
            # print("LAST", self.tools[maxuid])
            last_data = self.tools[max_uid]['data']
            last_offset = self.tools[max_uid]['offset']
            last_offset_value = self.tools[max_uid]['offset_value']
            last_type = self.tools[max_uid]['type']
            last_tool_type = self.tools[max_uid]['tool_type']
            last_solid_geometry = self.tools[max_uid]['solid_geometry']

            # if previous geometry was empty (it may happen for the first tool added)
            # then copy the object.solid_geometry
            if not last_solid_geometry:
                last_solid_geometry = self.solid_geometry

            self.tools.update({
                self.tooluid: {
                    'tooldia': tooldia,
                    'offset': last_offset,
                    'offset_value': last_offset_value,
                    'type': last_type,
                    'tool_type': last_tool_type,
                    'data': deepcopy(last_data),
                    'solid_geometry': deepcopy(last_solid_geometry)
                }
            })
            # print("CURRENT", self.tools[-1])

        self.ui.tool_offset_entry.hide()
        self.ui.tool_offset_lbl.hide()

        # we do this HACK to make sure the tools attribute to be serialized is updated in the self.ser_attrs list
        try:
            self.ser_attrs.remove('tools')
        except:
            pass
        self.ser_attrs.append('tools')

        if change_message is False:
            self.app.inform.emit(_(
                "[success] Tool added in Tool Table."
            ))
        else:
            change_message = False
            self.app.inform.emit(_(
                "[ERROR_NOTCL]Default Tool added. Wrong value format entered."
            ))
        self.build_ui()

    def on_tool_copy(self, all=None):
        self.ui_disconnect()

        # find the tool_uid maximum value in the self.tools
        uid_list = []
        for key in self.tools:
            uid_list.append(int(key))
        try:
            max_uid = max(uid_list, key=int)
        except ValueError:
            max_uid = 0

        if all is None:
            if self.ui.geo_tools_table.selectedItems():
                for current_row in self.ui.geo_tools_table.selectedItems():
                    # sometime the header get selected and it has row number -1
                    # we don't want to do anything with the header :)
                    if current_row.row() < 0:
                        continue
                    try:
                        tooluid_copy = int(self.ui.geo_tools_table.item(current_row.row(), 5).text())
                        self.set_tool_offset_visibility(current_row.row())
                        max_uid += 1
                        self.tools[int(max_uid)] = deepcopy(self.tools[tooluid_copy])
                    except AttributeError:
                        self.app.inform.emit(_(
                            "[WARNING_NOTCL]Failed. Select a tool to copy."
                        ))
                        self.build_ui()
                        return
                    except Exception as e:
                        log.debug("on_tool_copy() --> " + str(e))
                # deselect the table
                # self.ui.geo_tools_table.clearSelection()
            else:
                self.app.inform.emit(_(
                    "[WARNING_NOTCL]Failed. Select a tool to copy."
                ))
                self.build_ui()
                return
        else:
            # we copy all tools in geo_tools_table
            try:
                temp_tools = deepcopy(self.tools)
                max_uid += 1
                for tooluid in temp_tools:
                    self.tools[int(max_uid)] = deepcopy(temp_tools[tooluid])
                temp_tools.clear()
            except Exception as e:
                log.debug("on_tool_copy() --> " + str(e))

        # if there are no more tools in geo tools table then hide the tool offset
        if not self.tools:
            self.ui.tool_offset_entry.hide()
            self.ui.tool_offset_lbl.hide()

        # we do this HACK to make sure the tools attribute to be serialized is updated in the self.ser_attrs list
        try:
            self.ser_attrs.remove('tools')
        except:
            pass
        self.ser_attrs.append('tools')

        self.build_ui()
        self.app.inform.emit(_(
            "[success] Tool was copied in Tool Table."
        ))

    def on_tool_edit(self, current_item):

        self.ui_disconnect()

        current_row = current_item.row()
        try:
            d = float(self.ui.geo_tools_table.item(current_row, 1).text())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                d = float(self.ui.geo_tools_table.item(current_row, 1).text().replace(',', '.'))
            except ValueError:
                self.app.inform.emit(_(
                    "[ERROR_NOTCL]Wrong value format entered, "
                    "use a number."
                ))
                return

        tool_dia = float('%.4f' % d)
        tooluid = int(self.ui.geo_tools_table.item(current_row, 5).text())

        self.tools[tooluid]['tooldia'] = tool_dia

        try:
            self.ser_attrs.remove('tools')
            self.ser_attrs.append('tools')
        except:
            pass

        self.app.inform.emit(_(
            "[success] Tool was edited in Tool Table."
        ))
        self.build_ui()

    def on_tool_delete(self, all=None):

        self.ui_disconnect()

        if all is None:
            if self.ui.geo_tools_table.selectedItems():
                for current_row in self.ui.geo_tools_table.selectedItems():
                    # sometime the header get selected and it has row number -1
                    # we don't want to do anything with the header :)
                    if current_row.row() < 0:
                        continue
                    try:
                        tooluid_del = int(self.ui.geo_tools_table.item(current_row.row(), 5).text())
                        self.set_tool_offset_visibility(current_row.row())

                        temp_tools = deepcopy(self.tools)
                        for tooluid_key in self.tools:
                            if int(tooluid_key) == tooluid_del:
                                # if the self.tools has only one tool and we delete it then we move the solid_geometry
                                # as a property of the object otherwise there will be nothing to hold it
                                if len(self.tools) == 1:
                                    self.solid_geometry = deepcopy(self.tools[tooluid_key]['solid_geometry'])
                                temp_tools.pop(tooluid_del, None)
                        self.tools = deepcopy(temp_tools)
                        temp_tools.clear()
                    except AttributeError:
                        self.app.inform.emit(_(
                            "[WARNING_NOTCL]Failed. Select a tool to delete."
                        ))
                        self.build_ui()
                        return
                    except Exception as e:
                        log.debug("on_tool_delete() --> " + str(e))
                # deselect the table
                # self.ui.geo_tools_table.clearSelection()
            else:
                self.app.inform.emit(_(
                    "[WARNING_NOTCL]Failed. Select a tool to delete."
                ))
                self.build_ui()
                return
        else:
            # we delete all tools in geo_tools_table
            self.tools.clear()

        self.app.plot_all()

        # if there are no more tools in geo tools table then hide the tool offset
        if not self.tools:
            self.ui.tool_offset_entry.hide()
            self.ui.tool_offset_lbl.hide()

        # we do this HACK to make sure the tools attribute to be serialized is updated in the self.ser_attrs list
        try:
            self.ser_attrs.remove('tools')
        except:
            pass
        self.ser_attrs.append('tools')

        self.build_ui()
        self.app.inform.emit(_(
            "[success] Tool was deleted in Tool Table."
        ))

        obj_active = self.app.collection.get_active()
        # if the object was MultiGeo and now it has no tool at all (therefore no geometry)
        # we make it back SingleGeo
        if self.ui.geo_tools_table.rowCount() <= 0:
            obj_active.multigeo = False
            obj_active.options['xmin'] = 0
            obj_active.options['ymin'] = 0
            obj_active.options['xmax'] = 0
            obj_active.options['ymax'] = 0

        if obj_active.multigeo is True:
            try:
                xmin, ymin, xmax, ymax = obj_active.bounds()
                obj_active.options['xmin'] = xmin
                obj_active.options['ymin'] = ymin
                obj_active.options['xmax'] = xmax
                obj_active.options['ymax'] = ymax
            except:
                obj_active.options['xmin'] = 0
                obj_active.options['ymin'] = 0
                obj_active.options['xmax'] = 0
                obj_active.options['ymax'] = 0

    def on_row_selection_change(self):
        self.update_ui()

    def update_ui(self, row=None):
        self.ui_disconnect()

        if row is None:
            try:
                current_row = self.ui.geo_tools_table.currentRow()
            except:
                current_row = 0
        else:
            current_row = row

        if current_row < 0:
            current_row = 0

        self.set_tool_offset_visibility(current_row)

        # populate the form with the data from the tool associated with the row parameter
        try:
            tooluid = int(self.ui.geo_tools_table.item(current_row, 5).text())
        except Exception as e:
            log.debug("Tool missing. Add a tool in Geo Tool Table. %s" % str(e))
            return

        # update the form with the V-Shape fields if V-Shape selected in the geo_tool_table
        # also modify the Cut Z form entry to reflect the calculated Cut Z from values got from V-Shape Fields
        try:
            tool_type_txt = self.ui.geo_tools_table.cellWidget(current_row, 4).currentText()
            self.ui_update_v_shape(tool_type_txt=tool_type_txt)
        except Exception as e:
            log.debug("Tool missing. Add a tool in Geo Tool Table. %s" % str(e))
            return

        try:
            # set the form with data from the newly selected tool
            for tooluid_key, tooluid_value in self.tools.items():
                if int(tooluid_key) == tooluid:
                    for key, value in tooluid_value.items():
                        if key == 'data':
                            form_value_storage = tooluid_value[key]
                            self.update_form(form_value_storage)
                        if key == 'offset_value':
                            # update the offset value in the entry even if the entry is hidden
                            self.ui.tool_offset_entry.set_value(tooluid_value[key])

                        if key == 'tool_type' and value == 'V':
                            self.update_cutz()
        except Exception as e:
            log.debug("FlatCAMObj ---> update_ui() " + str(e))

        self.ui_connect()

    def ui_update_v_shape(self, tool_type_txt):
        if tool_type_txt == 'V':
            self.ui.tipdialabel.show()
            self.ui.tipdia_entry.show()
            self.ui.tipanglelabel.show()
            self.ui.tipangle_entry.show()
            self.ui.cutz_entry.setDisabled(True)

            self.update_cutz()
        else:
            self.ui.tipdialabel.hide()
            self.ui.tipdia_entry.hide()
            self.ui.tipanglelabel.hide()
            self.ui.tipangle_entry.hide()
            self.ui.cutz_entry.setDisabled(False)

    def update_cutz(self):
        try:
            vdia = float(self.ui.tipdia_entry.get_value())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                vdia = float(self.ui.tipdia_entry.get_value().replace(',', '.'))
            except ValueError:
                self.app.inform.emit(_(
                    "[ERROR_NOTCL]Wrong value format entered, "
                    "use a number."
                ))
                return

        try:
            half_vangle = float(self.ui.tipangle_entry.get_value()) / 2
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                half_vangle = float(self.ui.tipangle_entry.get_value().replace(',', '.')) / 2
            except ValueError:
                self.app.inform.emit(_(
                    "[ERROR_NOTCL]Wrong value format entered, "
                    "use a number."
                ))
                return


        row = self.ui.geo_tools_table.currentRow()
        tool_uid = int(self.ui.geo_tools_table.item(row, 5).text())

        tooldia = float(self.ui.geo_tools_table.item(row, 1).text())
        new_cutz = (tooldia - vdia) / (2 * math.tan(math.radians(half_vangle)))
        new_cutz = float('%.4f' % -new_cutz)
        self.ui.cutz_entry.set_value(new_cutz)

        # store the new CutZ value into storage (self.tools)
        for tooluid_key, tooluid_value in self.tools.items():
            if int(tooluid_key) == tool_uid:
                tooluid_value['data']['cutz'] = new_cutz

    def on_tooltable_cellwidget_change(self):
        cw = self.sender()
        cw_index = self.ui.geo_tools_table.indexAt(cw.pos())
        cw_row = cw_index.row()
        cw_col = cw_index.column()
        current_uid = int(self.ui.geo_tools_table.item(cw_row, 5).text())

        # store the text of the cellWidget that changed it's index in the self.tools
        for tooluid_key, tooluid_value in self.tools.items():
            if int(tooluid_key) == current_uid:
                cb_txt = cw.currentText()
                if cw_col == 2:
                    tooluid_value['offset'] = cb_txt
                    if cb_txt == _('Custom'):
                        self.ui.tool_offset_entry.show()
                        self.ui.tool_offset_lbl.show()
                    else:
                        self.ui.tool_offset_entry.hide()
                        self.ui.tool_offset_lbl.hide()
                        # reset the offset_value in storage self.tools
                        tooluid_value['offset_value'] = 0.0
                elif cw_col == 3:
                    # force toolpath type as 'Iso' if the tool type is V-Shape
                    if self.ui.geo_tools_table.cellWidget(cw_row, 4).currentText() == 'V':
                        tooluid_value['type'] = _('Iso')
                        idx = self.ui.geo_tools_table.cellWidget(cw_row, 3).findText(_('Iso'))
                        self.ui.geo_tools_table.cellWidget(cw_row, 3).setCurrentIndex(idx)
                    else:
                        tooluid_value['type'] = cb_txt
                elif cw_col == 4:
                    tooluid_value['tool_type'] = cb_txt

                    # if the tool_type selected is V-Shape then autoselect the toolpath type as Iso
                    if cb_txt == 'V':
                        idx = self.ui.geo_tools_table.cellWidget(cw_row, 3).findText(_('Iso'))
                        self.ui.geo_tools_table.cellWidget(cw_row, 3).setCurrentIndex(idx)
                self.ui_update_v_shape(tool_type_txt=self.ui.geo_tools_table.cellWidget(cw_row, 4).currentText())

    def update_form(self, dict_storage):
        for form_key in self.form_fields:
            for storage_key in dict_storage:
                if form_key == storage_key:
                    try:
                        self.form_fields[form_key].set_value(dict_storage[form_key])
                    except Exception as e:
                        log.debug(str(e))

        # this is done here because those buttons control through OptionalInputSelection if some entry's are Enabled
        # or not. But due of using the ui_disconnect() status is no longer updated and I had to do it here
        self.ui.ois_dwell_geo.on_cb_change()
        self.ui.ois_mpass_geo.on_cb_change()
        self.ui.ois_tcz_geo.on_cb_change()

    def gui_form_to_storage(self):

        self.ui_disconnect()
        widget_changed = self.sender()
        try:
            widget_idx = self.ui.grid3.indexOf(widget_changed)
        except:
            return

        # those are the indexes for the V-Tip Dia and V-Tip Angle, if edited calculate the new Cut Z
        if widget_idx == 1 or widget_idx == 3:
            self.update_cutz()

        # the original connect() function of the OptionalInpuSelection is no longer working because of the
        # ui_diconnect() so I use this 'hack'
        if isinstance(widget_changed, FCCheckBox):
            if widget_changed.text() == 'Multi-Depth:':
                self.ui.ois_mpass_geo.on_cb_change()

            if widget_changed.text() == 'Tool change':
                self.ui.ois_tcz_geo.on_cb_change()

            if widget_changed.text() == 'Dwell:':
                self.ui.ois_dwell_geo.on_cb_change()

        row = self.ui.geo_tools_table.currentRow()
        if row < 0:
            row = 0

        # store all the data associated with the row parameter to the self.tools storage
        tooldia_item = float(self.ui.geo_tools_table.item(row, 1).text())
        offset_item = self.ui.geo_tools_table.cellWidget(row, 2).currentText()
        type_item = self.ui.geo_tools_table.cellWidget(row, 3).currentText()
        tool_type_item = self.ui.geo_tools_table.cellWidget(row, 4).currentText()
        tooluid_item = int(self.ui.geo_tools_table.item(row, 5).text())

        try:
            offset_value_item = float(self.ui.tool_offset_entry.get_value())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                offset_value_item = float(self.ui.tool_offset_entry.get_value().replace(',', '.')
                                     )
            except ValueError:
                self.app.inform.emit(_(
                    "[ERROR_NOTCL]Wrong value format entered, "
                    "use a number."
                ))
                return

        # this new dict will hold the actual useful data, another dict that is the value of key 'data'
        temp_tools = {}
        temp_dia = {}
        temp_data = {}

        for tooluid_key, tooluid_value in self.tools.items():
            if int(tooluid_key) == tooluid_item:
                for key, value in tooluid_value.items():
                    if key == 'tooldia':
                        temp_dia[key] = tooldia_item
                    # update the 'offset', 'type' and 'tool_type' sections
                    if key == 'offset':
                        temp_dia[key] = offset_item
                    if key == 'type':
                        temp_dia[key] = type_item
                    if key == 'tool_type':
                        temp_dia[key] = tool_type_item
                    if key == 'offset_value':
                        temp_dia[key] = offset_value_item

                    if key == 'data':
                        # update the 'data' section
                        for data_key in tooluid_value[key].keys():
                            for form_key, form_value in self.form_fields.items():
                                if form_key == data_key:
                                    temp_data[data_key] = form_value.get_value()
                            # make sure we make a copy of the keys not in the form (we may use 'data' keys that are
                            # updated from self.app.defaults
                            if data_key not in self.form_fields:
                                temp_data[data_key] = value[data_key]
                        temp_dia[key] = deepcopy(temp_data)
                        temp_data.clear()

                    if key == 'solid_geometry':
                        temp_dia[key] = deepcopy(self.tools[tooluid_key]['solid_geometry'])

                    temp_tools[tooluid_key] = deepcopy(temp_dia)

            else:
                temp_tools[tooluid_key] = deepcopy(tooluid_value)

        self.tools.clear()
        self.tools = deepcopy(temp_tools)
        temp_tools.clear()
        self.ui_connect()

    def select_tools_table_row(self, row, clearsel=None):
        if clearsel:
            self.ui.geo_tools_table.clearSelection()

        if self.ui.geo_tools_table.rowCount() > 0:
            # self.ui.geo_tools_table.item(row, 0).setSelected(True)
            self.ui.geo_tools_table.setCurrentItem(self.ui.geo_tools_table.item(row, 0))

    def export_dxf(self):
        units = self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().upper()
        dwg = None
        try:
            dwg = ezdxf.new('R2010')
            msp = dwg.modelspace()

            def g2dxf(dxf_space, geo):
                if isinstance(geo, MultiPolygon):
                    for poly in geo:
                        ext_points = list(poly.exterior.coords)
                        dxf_space.add_lwpolyline(ext_points)
                        for interior in poly.interiors:
                            dxf_space.add_lwpolyline(list(interior.coords))
                if isinstance(geo, Polygon):
                    ext_points = list(geo.exterior.coords)
                    dxf_space.add_lwpolyline(ext_points)
                    for interior in geo.interiors:
                        dxf_space.add_lwpolyline(list(interior.coords))
                if isinstance(geo, MultiLineString):
                    for line in geo:
                        dxf_space.add_lwpolyline(list(line.coords))
                if isinstance(geo, LineString) or isinstance(geo, LinearRing):
                    dxf_space.add_lwpolyline(list(geo.coords))

            multigeo_solid_geometry = []
            if self.multigeo:
                for tool in self.tools:
                    multigeo_solid_geometry += self.tools[tool]['solid_geometry']
            else:
                    multigeo_solid_geometry = self.solid_geometry

            for geo in multigeo_solid_geometry:
                if type(geo) == list:
                    for g in geo:
                        g2dxf(msp, g)
                else:
                    g2dxf(msp, geo)

                # points = FlatCAMGeometry.get_pts(geo)
                # msp.add_lwpolyline(points)
        except Exception as e:
            log.debug(str(e))

        return dwg

    def get_selected_tools_table_items(self):
        """
        Returns a list of lists, each list in the list is made out of row elements

        :return: List of table_tools items.
        :rtype: list
        """
        table_tools_items = []
        if self.multigeo:
            for x in self.ui.geo_tools_table.selectedItems():
                table_tools_items.append([self.ui.geo_tools_table.item(x.row(), column).text()
                                          for column in range(0, self.ui.geo_tools_table.columnCount())])
        else:
            for x in self.ui.geo_tools_table.selectedItems():
                r = []
                # the last 2 columns for single-geo geometry are irrelevant and create problems reading
                # so we don't read them
                for column in range(0, self.ui.geo_tools_table.columnCount() - 2):
                    # the columns have items that have text but also have items that are widgets
                    # for which the text they hold has to be read differently
                    try:
                        txt = self.ui.geo_tools_table.item(x.row(), column).text()
                    except AttributeError:
                        txt = self.ui.geo_tools_table.cellWidget(x.row(), column).currentText()
                    except:
                        pass
                    r.append(txt)
                table_tools_items.append(r)

        for item in table_tools_items:
            item[0] = str(item[0])
        return table_tools_items

    def on_pp_changed(self):
        current_pp = self.ui.pp_geometry_name_cb.get_value()
        if current_pp == 'hpgl':
            self.old_pp_state = self.ui.mpass_cb.get_value()
            self.old_toolchangeg_state = self.ui.toolchangeg_cb.get_value()

            self.ui.mpass_cb.set_value(False)
            self.ui.mpass_cb.setDisabled(True)

            self.ui.toolchangeg_cb.set_value(True)
            self.ui.toolchangeg_cb.setDisabled(True)
        else:
            self.ui.mpass_cb.set_value(self.old_pp_state)
            self.ui.mpass_cb.setDisabled(False)

            self.ui.toolchangeg_cb.set_value(self.old_toolchangeg_state)
            self.ui.toolchangeg_cb.setDisabled(False)

        if "toolchange_probe" in current_pp.lower():
            self.ui.pdepth_entry.setVisible(True)
            self.ui.pdepth_label.show()

            self.ui.feedrate_probe_entry.setVisible(True)
            self.ui.feedrate_probe_label.show()
        else:
            self.ui.pdepth_entry.setVisible(False)
            self.ui.pdepth_label.hide()

            self.ui.feedrate_probe_entry.setVisible(False)
            self.ui.feedrate_probe_label.hide()

    def on_generatecnc_button_click(self, *args):

        self.app.report_usage("geometry_on_generatecnc_button")
        self.read_form()

        self.sel_tools = {}

        try:
            if self.special_group:
                self.app.inform.emit(_(
                    "[WARNING_NOTCL]This Geometry can't be processed because it is %s geometry."
                ) % str(self.special_group))
                return
        except AttributeError:
            pass

        # test to see if we have tools available in the tool table
        if self.ui.geo_tools_table.selectedItems():
            for x in self.ui.geo_tools_table.selectedItems():
                try:
                    tooldia = float(self.ui.geo_tools_table.item(x.row(), 1).text())
                except ValueError:
                    # try to convert comma to decimal point. if it's still not working error message and return
                    try:
                        tooldia = float(self.ui.geo_tools_table.item(x.row(), 1).text().replace(',', '.'))
                    except ValueError:
                        self.app.inform.emit(_(
                            "[ERROR_NOTCL]Wrong Tool Dia value format entered, "
                            "use a number."
                        ))
                        return
                tooluid = int(self.ui.geo_tools_table.item(x.row(), 5).text())

                for tooluid_key, tooluid_value in self.tools.items():
                    if int(tooluid_key) == tooluid:
                        self.sel_tools.update({
                            tooluid: deepcopy(tooluid_value)
                        })
            self.mtool_gen_cncjob()
            self.ui.geo_tools_table.clearSelection()

        elif self.ui.geo_tools_table.rowCount() == 1:
            tooluid = int(self.ui.geo_tools_table.item(0, 5).text())

            for tooluid_key, tooluid_value in self.tools.items():
                if int(tooluid_key) == tooluid:
                    self.sel_tools.update({
                        tooluid: deepcopy(tooluid_value)
                    })
            self.mtool_gen_cncjob()
            self.ui.geo_tools_table.clearSelection()

        else:
            self.app.inform.emit(_(
                "[ERROR_NOTCL] Failed. No tool selected in the tool table ..."
            ))

    def mtool_gen_cncjob(self, segx=None, segy=None, use_thread=True):
        """
        Creates a multi-tool CNCJob out of this Geometry object.
        The actual work is done by the target FlatCAMCNCjob object's
        `generate_from_geometry_2()` method.

        :param z_cut: Cut depth (negative)
        :param z_move: Hight of the tool when travelling (not cutting)
        :param feedrate: Feed rate while cutting on X - Y plane
        :param feedrate_z: Feed rate while cutting on Z plane
        :param feedrate_rapid: Feed rate while moving with rapids
        :param tooldia: Tool diameter
        :param outname: Name of the new object
        :param spindlespeed: Spindle speed (RPM)
        :param ppname_g Name of the postprocessor
        :return: None
        """

        offset_str = ''
        multitool_gcode = ''

        # use the name of the first tool selected in self.geo_tools_table which has the diameter passed as tool_dia
        outname = "%s_%s" % (self.options["name"], 'cnc')

        segx = segx if segx is not None else float(self.app.defaults['geometry_segx'])
        segy = segy if segy is not None else float(self.app.defaults['geometry_segy'])

        try:
            xmin = self.options['xmin']
            ymin = self.options['ymin']
            xmax = self.options['xmax']
            ymax = self.options['ymax']
        except Exception as e:
            log.debug("FlatCAMObj.FlatCAMGeometry.mtool_gen_cncjob() --> %s\n" % str(e))
            msg = _("[ERROR] An internal error has ocurred. See shell.\n")
            msg += _('FlatCAMObj.FlatCAMGeometry.mtool_gen_cncjob() --> %s') % str(e)
            msg += traceback.format_exc()
            self.app.inform.emit(msg)
            return

        # Object initialization function for app.new_object()
        # RUNNING ON SEPARATE THREAD!
        def job_init_single_geometry(job_obj, app_obj):
            assert isinstance(job_obj, FlatCAMCNCjob), \
                "Initializer expected a FlatCAMCNCjob, got %s" % type(job_obj)

            # count the tools
            tool_cnt = 0

            dia_cnc_dict = {}

            # this turn on the FlatCAMCNCJob plot for multiple tools
            job_obj.multitool = True
            job_obj.multigeo = False
            job_obj.cnc_tools.clear()
            # job_obj.create_geometry()

            job_obj.options['Tools_in_use'] = self.get_selected_tools_table_items()
            job_obj.segx = segx
            job_obj.segy = segy

            try:
                job_obj.z_pdepth = float(self.options["z_pdepth"])
            except ValueError:
                # try to convert comma to decimal point. if it's still not working error message and return
                try:
                    job_obj.z_pdepth = float(self.options["z_pdepth"].replace(',', '.'))
                except ValueError:
                    self.app.inform.emit(
                        _(
                            '[ERROR_NOTCL]Wrong value format for self.defaults["z_pdepth"] or self.options["z_pdepth"]'
                        ))

            try:
                job_obj.feedrate_probe = float(self.options["feedrate_probe"])
            except ValueError:
                # try to convert comma to decimal point. if it's still not working error message and return
                try:
                    job_obj.feedrate_rapid = float(self.options["feedrate_probe"].replace(',', '.'))
                except ValueError:
                    self.app.inform.emit(
                        _(
                            '[ERROR_NOTCL]Wrong value format for self.defaults["feedrate_probe"] '
                            'or self.options["feedrate_probe"]'
                        ))

            for tooluid_key in self.sel_tools:
                tool_cnt += 1
                app_obj.progress.emit(20)

                for diadict_key, diadict_value in self.sel_tools[tooluid_key].items():
                    if diadict_key == 'tooldia':
                        tooldia_val = float('%.4f' % float(diadict_value))
                        dia_cnc_dict.update({
                            diadict_key: tooldia_val
                        })
                    if diadict_key == 'offset':
                        o_val = diadict_value.lower()
                        dia_cnc_dict.update({
                            diadict_key: o_val
                        })

                    if diadict_key == 'type':
                        t_val = diadict_value
                        dia_cnc_dict.update({
                            diadict_key: t_val
                        })

                    if diadict_key == 'tool_type':
                        tt_val = diadict_value
                        dia_cnc_dict.update({
                            diadict_key: tt_val
                        })

                    if diadict_key == 'data':
                        for data_key, data_value in diadict_value.items():
                            if data_key ==  "multidepth":
                                multidepth = data_value
                            if data_key == "depthperpass":
                                depthpercut = data_value

                            if data_key == "extracut":
                                extracut = data_value
                            if data_key == "startz":
                                startz = data_value
                            if data_key == "endz":
                                endz = data_value

                            if data_key == "toolchangez":
                                toolchangez =data_value
                            if data_key == "toolchangexy":
                                toolchangexy = data_value
                            if data_key == "toolchange":
                                toolchange = data_value

                            if data_key == "cutz":
                                z_cut = data_value
                            if data_key == "travelz":
                                z_move = data_value

                            if data_key == "feedrate":
                                feedrate = data_value
                            if data_key == "feedrate_z":
                                feedrate_z = data_value
                            if data_key == "feedrate_rapid":
                                feedrate_rapid = data_value

                            if data_key == "ppname_g":
                                pp_geometry_name = data_value

                            if data_key == "spindlespeed":
                                spindlespeed = data_value
                            if data_key == "dwell":
                                dwell = data_value
                            if data_key == "dwelltime":
                                dwelltime = data_value

                        datadict = deepcopy(diadict_value)
                        dia_cnc_dict.update({
                            diadict_key: datadict
                        })

                if dia_cnc_dict['offset'] == 'in':
                    tool_offset = -dia_cnc_dict['tooldia'] / 2
                    offset_str = 'inside'
                elif dia_cnc_dict['offset'].lower() == 'out':
                    tool_offset = dia_cnc_dict['tooldia']  / 2
                    offset_str = 'outside'
                elif dia_cnc_dict['offset'].lower() == 'path':
                    offset_str = 'onpath'
                    tool_offset = 0.0
                else:
                    offset_str = 'custom'
                    try:
                        offset_value = float(self.ui.tool_offset_entry.get_value())
                    except ValueError:
                        # try to convert comma to decimal point. if it's still not working error message and return
                        try:
                            offset_value = float(self.ui.tool_offset_entry.get_value().replace(',', '.')
                                                 )
                        except ValueError:
                            self.app.inform.emit(_(
                                "[ERROR_NOTCL]Wrong value format entered, "
                                "use a number."
                            ))
                            return
                    if offset_value:
                        tool_offset = float(offset_value)
                    else:
                        self.app.inform.emit(
                            _(
                                "[WARNING] Tool Offset is selected in Tool Table but no value is provided.\n"
                                "Add a Tool Offset or change the Offset Type."
                            )
                        )
                        return
                dia_cnc_dict.update({
                    'offset_value': tool_offset
                })

                job_obj.coords_decimals = self.app.defaults["cncjob_coords_decimals"]
                job_obj.fr_decimals = self.app.defaults["cncjob_fr_decimals"]

                # Propagate options
                job_obj.options["tooldia"] = tooldia_val
                job_obj.options['type'] = 'Geometry'
                job_obj.options['tool_dia'] = tooldia_val

                job_obj.options['xmin'] = xmin
                job_obj.options['ymin'] = ymin
                job_obj.options['xmax'] = xmax
                job_obj.options['ymax'] = ymax

                app_obj.progress.emit(40)

                res = job_obj.generate_from_geometry_2(
                    self, tooldia=tooldia_val, offset=tool_offset, tolerance=0.0005,
                    z_cut=z_cut, z_move=z_move,
                    feedrate=feedrate, feedrate_z=feedrate_z, feedrate_rapid=feedrate_rapid,
                    spindlespeed=spindlespeed, dwell=dwell, dwelltime=dwelltime,
                    multidepth=multidepth, depthpercut=depthpercut,
                    extracut=extracut, startz=startz, endz=endz,
                    toolchange=toolchange, toolchangez=toolchangez, toolchangexy=toolchangexy,
                    pp_geometry_name=pp_geometry_name,
                    tool_no=tool_cnt)

                if res == 'fail':
                    log.debug("FlatCAMGeometry.mtool_gen_cncjob() --> generate_from_geometry2() failed")
                    return 'fail'
                else:
                    dia_cnc_dict['gcode'] = res

                app_obj.progress.emit(50)
                # tell gcode_parse from which point to start drawing the lines depending on what kind of
                # object is the source of gcode
                job_obj.toolchange_xy_type = "geometry"

                dia_cnc_dict['gcode_parsed'] = job_obj.gcode_parse()

                # TODO this serve for bounding box creation only; should be optimized
                dia_cnc_dict['solid_geometry'] = cascaded_union([geo['geom'] for geo in dia_cnc_dict['gcode_parsed']])

                app_obj.progress.emit(80)

                job_obj.cnc_tools.update({
                    tooluid_key: deepcopy(dia_cnc_dict)
                })
                dia_cnc_dict.clear()

        # Object initialization function for app.new_object()
        # RUNNING ON SEPARATE THREAD!
        def job_init_multi_geometry(job_obj, app_obj):
            assert isinstance(job_obj, FlatCAMCNCjob), \
                "Initializer expected a FlatCAMCNCjob, got %s" % type(job_obj)

            # count the tools
            tool_cnt = 0

            dia_cnc_dict = {}

            current_uid = int(1)

            # this turn on the FlatCAMCNCJob plot for multiple tools
            job_obj.multitool = True
            job_obj.multigeo = True
            job_obj.cnc_tools.clear()

            job_obj.options['xmin'] = xmin
            job_obj.options['ymin'] = ymin
            job_obj.options['xmax'] = xmax
            job_obj.options['ymax'] = ymax

            try:
                job_obj.z_pdepth = float(self.options["z_pdepth"])
            except ValueError:
                # try to convert comma to decimal point. if it's still not working error message and return
                try:
                    job_obj.z_pdepth = float(self.options["z_pdepth"].replace(',', '.'))
                except ValueError:
                    self.app.inform.emit(
                        _(
                            '[ERROR_NOTCL]Wrong value format for self.defaults["z_pdepth"] or self.options["z_pdepth"]'
                        ))

            try:
                job_obj.feedrate_probe = float(self.options["feedrate_probe"])
            except ValueError:
                # try to convert comma to decimal point. if it's still not working error message and return
                try:
                    job_obj.feedrate_rapid = float(self.options["feedrate_probe"].replace(',', '.'))
                except ValueError:
                    self.app.inform.emit(
                        _(
                            '[ERROR_NOTCL]Wrong value format for self.defaults["feedrate_probe"] '
                            'or self.options["feedrate_probe"]'
                        ))

            # make sure that trying to make a CNCJob from an empty file is not creating an app crash
            if not self.solid_geometry:
                a = 0
                for tooluid_key in self.tools:
                    if self.tools[tooluid_key]['solid_geometry'] is None:
                        a += 1
                if a == len(self.tools):
                    self.app.inform.emit(_(
                        '[ERROR_NOTCL]Cancelled. Empty file, it has no geometry...'
                    ))
                    return 'fail'

            for tooluid_key in self.sel_tools:
                tool_cnt += 1
                app_obj.progress.emit(20)

                # find the tool_dia associated with the tooluid_key
                sel_tool_dia = self.sel_tools[tooluid_key]['tooldia']

                # search in the self.tools for the sel_tool_dia and when found see what tooluid has
                # on the found tooluid in self.tools we also have the solid_geometry that interest us
                for k, v in self.tools.items():
                    if float('%.4f' % float(v['tooldia'])) == float('%.4f' % float(sel_tool_dia)):
                        current_uid = int(k)
                        break

                for diadict_key, diadict_value in self.sel_tools[tooluid_key].items():
                    if diadict_key == 'tooldia':
                        tooldia_val = float('%.4f' % float(diadict_value))
                        dia_cnc_dict.update({
                            diadict_key: tooldia_val
                        })
                    if diadict_key == 'offset':
                        o_val = diadict_value.lower()
                        dia_cnc_dict.update({
                            diadict_key: o_val
                        })

                    if diadict_key == 'type':
                        t_val = diadict_value
                        dia_cnc_dict.update({
                            diadict_key: t_val
                        })

                    if diadict_key == 'tool_type':
                        tt_val = diadict_value
                        dia_cnc_dict.update({
                            diadict_key: tt_val
                        })

                    if diadict_key == 'data':
                        for data_key, data_value in diadict_value.items():
                            if data_key ==  "multidepth":
                                multidepth = data_value
                            if data_key == "depthperpass":
                                depthpercut = data_value

                            if data_key == "extracut":
                                extracut = data_value
                            if data_key == "startz":
                                startz = data_value
                            if data_key == "endz":
                                endz = data_value

                            if data_key == "toolchangez":
                                toolchangez =data_value
                            if data_key == "toolchangexy":
                                toolchangexy = data_value
                            if data_key == "toolchange":
                                toolchange = data_value

                            if data_key == "cutz":
                                z_cut = data_value
                            if data_key == "travelz":
                                z_move = data_value

                            if data_key == "feedrate":
                                feedrate = data_value
                            if data_key == "feedrate_z":
                                feedrate_z = data_value
                            if data_key == "feedrate_rapid":
                                feedrate_rapid = data_value

                            if data_key == "ppname_g":
                                pp_geometry_name = data_value

                            if data_key == "spindlespeed":
                                spindlespeed = data_value
                            if data_key == "dwell":
                                dwell = data_value
                            if data_key == "dwelltime":
                                dwelltime = data_value

                        datadict = deepcopy(diadict_value)
                        dia_cnc_dict.update({
                            diadict_key: datadict
                        })

                if dia_cnc_dict['offset'] == 'in':
                    tool_offset = -dia_cnc_dict['tooldia'] / 2
                    offset_str = 'inside'
                elif dia_cnc_dict['offset'].lower() == 'out':
                    tool_offset = dia_cnc_dict['tooldia']  / 2
                    offset_str = 'outside'
                elif dia_cnc_dict['offset'].lower() == 'path':
                    offset_str = 'onpath'
                    tool_offset = 0.0
                else:
                    offset_str = 'custom'
                    try:
                        offset_value = float(self.ui.tool_offset_entry.get_value())
                    except ValueError:
                        # try to convert comma to decimal point. if it's still not working error message and return
                        try:
                            offset_value = float(self.ui.tool_offset_entry.get_value().replace(',', '.')
                                                  )
                        except ValueError:
                            self.app.inform.emit(_(
                                "[ERROR_NOTCL]Wrong value format entered, "
                                "use a number."
                            ))
                            return
                    if offset_value:
                        tool_offset = float(offset_value)
                    else:
                        self.app.inform.emit(
                            _(
                                "[WARNING] Tool Offset is selected in Tool Table but no value is provided.\n"
                                "Add a Tool Offset or change the Offset Type."
                            )
                        )
                        return
                dia_cnc_dict.update({
                    'offset_value': tool_offset
                })

                job_obj.coords_decimals = self.app.defaults["cncjob_coords_decimals"]
                job_obj.fr_decimals = self.app.defaults["cncjob_fr_decimals"]

                # Propagate options
                job_obj.options["tooldia"] = tooldia_val
                job_obj.options['type'] = 'Geometry'
                job_obj.options['tool_dia'] = tooldia_val

                app_obj.progress.emit(40)

                tool_solid_geometry = self.tools[current_uid]['solid_geometry']
                res = job_obj.generate_from_multitool_geometry(
                    tool_solid_geometry, tooldia=tooldia_val, offset=tool_offset,
                    tolerance=0.0005, z_cut=z_cut, z_move=z_move,
                    feedrate=feedrate, feedrate_z=feedrate_z, feedrate_rapid=feedrate_rapid,
                    spindlespeed=spindlespeed, dwell=dwell, dwelltime=dwelltime,
                    multidepth=multidepth, depthpercut=depthpercut,
                    extracut=extracut, startz=startz, endz=endz,
                    toolchange=toolchange, toolchangez=toolchangez, toolchangexy=toolchangexy,
                    pp_geometry_name=pp_geometry_name,
                    tool_no=tool_cnt)

                if res == 'fail':
                    log.debug("FlatCAMGeometry.mtool_gen_cncjob() --> generate_from_geometry2() failed")
                    return 'fail'
                else:
                    dia_cnc_dict['gcode'] = res

                dia_cnc_dict['gcode_parsed'] = job_obj.gcode_parse()

                # TODO this serve for bounding box creation only; should be optimized
                dia_cnc_dict['solid_geometry'] = cascaded_union([geo['geom'] for geo in dia_cnc_dict['gcode_parsed']])

                # tell gcode_parse from which point to start drawing the lines depending on what kind of
                # object is the source of gcode
                job_obj.toolchange_xy_type = "geometry"

                app_obj.progress.emit(80)

                job_obj.cnc_tools.update({
                    tooluid_key: deepcopy(dia_cnc_dict)
                })
                dia_cnc_dict.clear()

        if use_thread:
            # To be run in separate thread
            # The idea is that if there is a solid_geometry in the file "root" then most likely thare are no
            # separate solid_geometry in the self.tools dictionary
            def job_thread(app_obj):
                if self.solid_geometry:
                    with self.app.proc_container.new(_("Generating CNC Code")):
                        if app_obj.new_object("cncjob", outname, job_init_single_geometry) != 'fail':
                            app_obj.inform.emit("[success]CNCjob created: %s" % outname)
                            app_obj.progress.emit(100)
                else:
                    with self.app.proc_container.new(_("Generating CNC Code")):
                        if app_obj.new_object("cncjob", outname, job_init_multi_geometry) != 'fail':
                            app_obj.inform.emit("[success]CNCjob created: %s" % outname)
                            app_obj.progress.emit(100)

            # Create a promise with the name
            self.app.collection.promise(outname)
            # Send to worker
            self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})
        else:
            if self.solid_geometry:
                self.app.new_object("cncjob", outname, job_init_single_geometry)
            else:
                self.app.new_object("cncjob", outname, job_init_multi_geometry)


    def generatecncjob(self, outname=None,
                       tooldia=None, offset=None,
                       z_cut=None, z_move=None,
                       feedrate=None, feedrate_z=None, feedrate_rapid=None,
                       spindlespeed=None, dwell=None, dwelltime=None,
                       multidepth=None, depthperpass=None,
                       toolchange=None, toolchangez=None, toolchangexy=None,
                       extracut=None, startz=None, endz=None,
                       ppname_g=None,
                       segx=None,
                       segy=None,
                       use_thread=True):
        """
        Only used for TCL Command.
        Creates a CNCJob out of this Geometry object. The actual
        work is done by the target FlatCAMCNCjob object's
        `generate_from_geometry_2()` method.

        :param z_cut: Cut depth (negative)
        :param z_move: Hight of the tool when travelling (not cutting)
        :param feedrate: Feed rate while cutting on X - Y plane
        :param feedrate_z: Feed rate while cutting on Z plane
        :param feedrate_rapid: Feed rate while moving with rapids
        :param tooldia: Tool diameter
        :param outname: Name of the new object
        :param spindlespeed: Spindle speed (RPM)
        :param ppname_g Name of the postprocessor
        :return: None
        """

        tooldia = tooldia if tooldia else float(self.options["cnctooldia"])
        outname = outname if outname is not None else self.options["name"]

        z_cut = z_cut if z_cut is not None else float(self.options["cutz"])
        z_move = z_move if z_move is not None else float(self.options["travelz"])

        feedrate = feedrate if feedrate is not None else float(self.options["feedrate"])
        feedrate_z = feedrate_z if feedrate_z is not None else float(self.options["feedrate_z"])
        feedrate_rapid = feedrate_rapid if feedrate_rapid is not None else float(self.options["feedrate_rapid"])

        multidepth = multidepth if multidepth is not None else self.options["multidepth"]
        depthperpass = depthperpass if depthperpass is not None else float(self.options["depthperpass"])

        segx = segx if segx is not None else float(self.app.defaults['geometry_segx'])
        segy = segy if segy is not None else float(self.app.defaults['geometry_segy'])

        extracut = extracut if extracut is not None else float(self.options["extracut"])
        startz = startz if startz is not None else self.options["startz"]
        endz = endz if endz is not None else float(self.options["endz"])

        toolchangez = toolchangez if toolchangez else float(self.options["toolchangez"])
        toolchangexy = toolchangexy if toolchangexy else self.options["toolchangexy"]
        toolchange = toolchange if toolchange else self.options["toolchange"]

        offset = offset if offset else 0.0

        # int or None.
        spindlespeed = spindlespeed if spindlespeed else self.options['spindlespeed']
        dwell = dwell if dwell else self.options["dwell"]
        dwelltime = dwelltime if dwelltime else float(self.options["dwelltime"])

        ppname_g = ppname_g if ppname_g else self.options["ppname_g"]

        # Object initialization function for app.new_object()
        # RUNNING ON SEPARATE THREAD!
        def job_init(job_obj, app_obj):
            assert isinstance(job_obj, FlatCAMCNCjob), "Initializer expected a FlatCAMCNCjob, got %s" % type(job_obj)

            # Propagate options
            job_obj.options["tooldia"] = tooldia

            app_obj.progress.emit(20)

            job_obj.coords_decimals = self.app.defaults["cncjob_coords_decimals"]
            job_obj.fr_decimals = self.app.defaults["cncjob_fr_decimals"]
            app_obj.progress.emit(40)

            job_obj.options['type'] = 'Geometry'
            job_obj.options['tool_dia'] = tooldia

            job_obj.segx = segx
            job_obj.segy = segy

            try:
                job_obj.z_pdepth = float(self.options["z_pdepth"])
            except ValueError:
                # try to convert comma to decimal point. if it's still not working error message and return
                try:
                    job_obj.z_pdepth = float(self.options["z_pdepth"].replace(',', '.'))
                except ValueError:
                    self.app.inform.emit(
                        _(
                            '[ERROR_NOTCL]Wrong value format for self.defaults["z_pdepth"] or self.options["z_pdepth"]'
                        ))

            try:
                job_obj.feedrate_probe = float(self.options["feedrate_probe"])
            except ValueError:
                # try to convert comma to decimal point. if it's still not working error message and return
                try:
                    job_obj.feedrate_rapid = float(self.options["feedrate_probe"].replace(',', '.'))
                except ValueError:
                    self.app.inform.emit(
                        _(
                            '[ERROR_NOTCL]Wrong value format for self.defaults["feedrate_probe"] '
                            'or self.options["feedrate_probe"]'
                        ))

            # TODO: The tolerance should not be hard coded. Just for testing.
            job_obj.generate_from_geometry_2(self, tooldia=tooldia, offset=offset, tolerance=0.0005,
                                             z_cut=z_cut, z_move=z_move,
                                             feedrate=feedrate, feedrate_z=feedrate_z, feedrate_rapid=feedrate_rapid,
                                             spindlespeed=spindlespeed, dwell=dwell, dwelltime=dwelltime,
                                             multidepth=multidepth, depthpercut=depthperpass,
                                             toolchange=toolchange, toolchangez=toolchangez, toolchangexy=toolchangexy,
                                             extracut=extracut, startz=startz, endz=endz,
                                             pp_geometry_name=ppname_g
                                             )

            app_obj.progress.emit(50)
            # tell gcode_parse from which point to start drawing the lines depending on what kind of object is the
            # source of gcode
            job_obj.toolchange_xy_type = "geometry"
            job_obj.gcode_parse()

            app_obj.progress.emit(80)

        if use_thread:
            # To be run in separate thread
            def job_thread(app_obj):
                with self.app.proc_container.new(_("Generating CNC Code")):
                    app_obj.new_object("cncjob", outname, job_init)
                    app_obj.inform.emit("[success]CNCjob created: %s" % outname)
                    app_obj.progress.emit(100)

            # Create a promise with the name
            self.app.collection.promise(outname)
            # Send to worker
            self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})
        else:
            self.app.new_object("cncjob", outname, job_init)

    # def on_plot_cb_click(self, *args):  # TODO: args not needed
    #     if self.muted_ui:
    #         return
    #     self.read_form_item('plot')

    def scale(self, xfactor, yfactor=None, point=None):
        """
        Scales all geometry by a given factor.

        :param xfactor: Factor by which to scale the object's geometry/
        :type xfactor: float
        :param yfactor: Factor by which to scale the object's geometry/
        :type yfactor: float
        :return: None
        :rtype: None
        """

        try:
            xfactor = float(xfactor)
        except:
            self.app.inform.emit(_(
                "[ERROR_NOTCL] Scale factor has to be a number: integer or float."))
            return

        if yfactor is None:
            yfactor = xfactor
        else:
            try:
                yfactor = float(yfactor)
            except:
                self.app.inform.emit(_(
                    "[ERROR_NOTCL] Scale factor has to be a number: integer or float."
                ))
                return

        if point is None:
            px = 0
            py = 0
        else:
            px, py = point

        # if type(self.solid_geometry) == list:
        #     geo_list =  self.flatten(self.solid_geometry)
        #     self.solid_geometry = []
        #     # for g in geo_list:
        #     #     self.solid_geometry.append(affinity.scale(g, xfactor, yfactor, origin=(px, py)))
        #     self.solid_geometry = [affinity.scale(g, xfactor, yfactor, origin=(px, py))
        #                            for g in geo_list]
        # else:
        #     self.solid_geometry = affinity.scale(self.solid_geometry, xfactor, yfactor,
        #                                          origin=(px, py))
        # self.app.inform.emit("[success]Geometry Scale done.")

        def scale_recursion(geom):
            if type(geom) == list:
                geoms=list()
                for local_geom in geom:
                    geoms.append(scale_recursion(local_geom))
                return geoms
            else:
                return  affinity.scale(geom, xfactor, yfactor, origin=(px, py))

        if self.multigeo is True:
            for tool in self.tools:
                self.tools[tool]['solid_geometry'] = scale_recursion(self.tools[tool]['solid_geometry'])
        else:
            self.solid_geometry=scale_recursion(self.solid_geometry)

        self.app.inform.emit(_(
            "[success]Geometry Scale done."
        ))

    def offset(self, vect):
        """
        Offsets all geometry by a given vector/

        :param vect: (x, y) vector by which to offset the object's geometry.
        :type vect: tuple
        :return: None
        :rtype: None
        """

        try:
            dx, dy = vect
        except TypeError:
            self.app.inform.emit(_(
                "[ERROR_NOTCL]An (x,y) pair of values are needed. "
                "Probable you entered only one value in the Offset field."
            ))
            return

        def translate_recursion(geom):
            if type(geom) == list:
                geoms=list()
                for local_geom in geom:
                    geoms.append(translate_recursion(local_geom))
                return geoms
            else:
                return  affinity.translate(geom, xoff=dx, yoff=dy)

        if self.multigeo is True:
            for tool in self.tools:
                self.tools[tool]['solid_geometry'] = translate_recursion(self.tools[tool]['solid_geometry'])
        else:
            self.solid_geometry=translate_recursion(self.solid_geometry)
        self.app.inform.emit(_(
            "[success]Geometry Offset done."
        ))

    def convert_units(self, units):
        self.ui_disconnect()

        factor = Geometry.convert_units(self, units)

        self.options['cutz'] = float(self.options['cutz']) * factor
        self.options['depthperpass'] = float(self.options['depthperpass']) * factor
        self.options['travelz'] = float(self.options['travelz']) * factor
        self.options['feedrate'] = float(self.options['feedrate']) * factor
        self.options['feedrate_z'] = float(self.options['feedrate_z']) * factor
        self.options['feedrate_rapid'] = float(self.options['feedrate_rapid']) * factor
        self.options['endz'] = float(self.options['endz']) * factor
        # self.options['cnctooldia'] *= factor
        # self.options['painttooldia'] *= factor
        # self.options['paintmargin'] *= factor
        # self.options['paintoverlap'] *= factor

        self.options["toolchangez"] = float(self.options["toolchangez"]) * factor

        if self.app.defaults["geometry_toolchangexy"] == '':
            self.options['toolchangexy'] = "0.0, 0.0"
        else:
            coords_xy = [float(eval(coord)) for coord in self.app.defaults["geometry_toolchangexy"].split(",")]
            if len(coords_xy) < 2:
                self.app.inform.emit(_(
                    "[ERROR]The Toolchange X,Y field in Edit -> Preferences has to be "
                    "in the format (x, y) \nbut now there is only one value, not two. "
                ))
                return 'fail'
            coords_xy[0] *= factor
            coords_xy[1] *= factor
            self.options['toolchangexy'] = "%f, %f" % (coords_xy[0], coords_xy[1])

        if self.options['startz'] is not None:
            self.options['startz'] = float(self.options['startz']) * factor

        param_list = ['cutz', 'depthperpass', 'travelz', 'feedrate', 'feedrate_z', 'feedrate_rapid',
                      'endz', 'toolchangez']

        if isinstance(self, FlatCAMGeometry):
            temp_tools_dict = {}
            tool_dia_copy = {}
            data_copy = {}
            for tooluid_key, tooluid_value in self.tools.items():
                for dia_key, dia_value in tooluid_value.items():
                    if dia_key == 'tooldia':
                        dia_value *= factor
                        dia_value = float('%.4f' % dia_value)
                        tool_dia_copy[dia_key] = dia_value
                    if dia_key == 'offset':
                        tool_dia_copy[dia_key] = dia_value
                    if dia_key == 'offset_value':
                        dia_value *= factor
                        tool_dia_copy[dia_key] = dia_value

                        # convert the value in the Custom Tool Offset entry in UI
                        custom_offset = None
                        try:
                            custom_offset = float(self.ui.tool_offset_entry.get_value())
                        except ValueError:
                            # try to convert comma to decimal point. if it's still not working error message and return
                            try:
                                custom_offset = float(self.ui.tool_offset_entry.get_value().replace(',', '.')
                                )
                            except ValueError:
                                self.app.inform.emit(_(
                                    "[ERROR_NOTCL]Wrong value format entered, "
                                    "use a number."
                                ))
                                return
                        except TypeError:
                            pass

                        if custom_offset:
                            custom_offset *= factor
                            self.ui.tool_offset_entry.set_value(custom_offset)

                    if dia_key == 'type':
                        tool_dia_copy[dia_key] = dia_value
                    if dia_key == 'tool_type':
                        tool_dia_copy[dia_key] = dia_value
                    if dia_key == 'data':
                        for data_key, data_value in dia_value.items():
                            # convert the form fields that are convertible
                            for param in param_list:
                                if data_key == param and data_value is not None:
                                    data_copy[data_key] = data_value * factor
                            # copy the other dict entries that are not convertible
                            if data_key not in param_list:
                                data_copy[data_key] = data_value
                        tool_dia_copy[dia_key] = deepcopy(data_copy)
                        data_copy.clear()

                temp_tools_dict.update({
                    tooluid_key: deepcopy(tool_dia_copy)
                })
                tool_dia_copy.clear()

            self.tools.clear()
            self.tools = deepcopy(temp_tools_dict)

        # if there is a value in the new tool field then convert that one too
        tooldia = self.ui.addtool_entry.get_value()
        if tooldia:
            tooldia *= factor
            # limit the decimals to 2 for METRIC and 3 for INCH
            if units.lower() == 'in':
                tooldia = float('%.4f' % tooldia)
            else:
                tooldia = float('%.2f' % tooldia)

            self.ui.addtool_entry.set_value(tooldia)

        return factor

    def plot_element(self, element, color='red', visible=None):

        visible = visible if visible else self.options['plot']

        try:
            for sub_el in element:
                self.plot_element(sub_el)

        except TypeError:  # Element is not iterable...
            self.add_shape(shape=element, color=color, visible=visible, layer=0)

    def plot(self, visible=None):
        """
        Adds the object into collection.

        :return: None
        """

        # Does all the required setup and returns False
        # if the 'ptint' option is set to False.
        if not FlatCAMObj.plot(self):
            return

        try:
            # plot solid geometries found as members of self.tools attribute dict
            # for MultiGeo
            if self.multigeo == True: # geo multi tool usage
                for tooluid_key in self.tools:
                    solid_geometry = self.tools[tooluid_key]['solid_geometry']
                    self.plot_element(solid_geometry, visible=visible)

            # plot solid geometry that may be an direct attribute of the geometry object
            # for SingleGeo
            if self.solid_geometry:
                self.plot_element(self.solid_geometry, visible=visible)

            # self.plot_element(self.solid_geometry, visible=self.options['plot'])
            self.shapes.redraw()
        except (ObjectDeleted, AttributeError):
            self.shapes.clear(update=True)

    def on_plot_cb_click(self, *args):
        if self.muted_ui:
            return
        self.plot()
        self.read_form_item('plot')

        self.ui_disconnect()
        cb_flag = self.ui.plot_cb.isChecked()
        for row in range(self.ui.geo_tools_table.rowCount()):
            table_cb = self.ui.geo_tools_table.cellWidget(row, 6)
            if cb_flag:
                table_cb.setChecked(True)
            else:
                table_cb.setChecked(False)
        self.ui_connect()

    def on_plot_cb_click_table(self):
        # self.ui.cnc_tools_table.cellWidget(row, 2).widget().setCheckState(QtCore.Qt.Unchecked)
        self.ui_disconnect()
        cw = self.sender()
        cw_index = self.ui.geo_tools_table.indexAt(cw.pos())
        cw_row = cw_index.row()
        check_row = 0

        self.shapes.clear(update=True)
        for tooluid_key in self.tools:
            solid_geometry = self.tools[tooluid_key]['solid_geometry']

            # find the geo_tool_table row associated with the tooluid_key
            for row in range(self.ui.geo_tools_table.rowCount()):
                tooluid_item = int(self.ui.geo_tools_table.item(row, 5).text())
                if tooluid_item == int(tooluid_key):
                    check_row = row
                    break
            if self.ui.geo_tools_table.cellWidget(check_row, 6).isChecked():
                self.plot_element(element=solid_geometry, visible=True)
        self.shapes.redraw()

        # make sure that the general plot is disabled if one of the row plot's are disabled and
        # if all the row plot's are enabled also enable the general plot checkbox
        cb_cnt = 0
        total_row = self.ui.geo_tools_table.rowCount()
        for row in range(total_row):
            if self.ui.geo_tools_table.cellWidget(row, 6).isChecked():
                cb_cnt += 1
            else:
                cb_cnt -= 1
        if cb_cnt < total_row:
            self.ui.plot_cb.setChecked(False)
        else:
            self.ui.plot_cb.setChecked(True)
        self.ui_connect()


class FlatCAMCNCjob(FlatCAMObj, CNCjob):
    """
    Represents G-Code.
    """
    optionChanged = QtCore.pyqtSignal(str)
    ui_type = CNCObjectUI

    def __init__(self, name, units="in", kind="generic", z_move=0.1,
                 feedrate=3.0, feedrate_rapid=3.0, z_cut=-0.002, tooldia=0.0,
                 spindlespeed=None):

        FlatCAMApp.App.log.debug("Creating CNCJob object...")

        CNCjob.__init__(self, units=units, kind=kind, z_move=z_move,
                        feedrate=feedrate, feedrate_rapid=feedrate_rapid, z_cut=z_cut, tooldia=tooldia,
                        spindlespeed=spindlespeed, steps_per_circle=int(self.app.defaults["cncjob_steps_per_circle"]))

        FlatCAMObj.__init__(self, name)

        self.kind = "cncjob"

        self.options.update({
            "plot": True,
            "tooldia": 0.03937,  # 0.4mm in inches
            "append": "",
            "prepend": "",
            "dwell": False,
            "dwelltime": 1,
            "type": 'Geometry',
            "toolchange_macro": '',
            "toolchange_macro_enable": False
        })

        '''
            This is a dict of dictionaries. Each dict is associated with a tool present in the file. The key is the 
            diameter of the tools and the value is another dict that will hold the data under the following form:
               {tooldia:   {
                           'tooluid': 1,
                           'offset': 'Path',
                           'type_item': 'Rough',
                           'tool_type': 'C1',
                           'data': {} # a dict to hold the parameters
                           'gcode': "" # a string with the actual GCODE
                           'gcode_parsed': {} # dictionary holding the CNCJob geometry and type of geometry (cut or move)
                           'solid_geometry': []
                           },
                           ...
               }
            It is populated in the FlatCAMGeometry.mtool_gen_cncjob()
            BEWARE: I rely on the ordered nature of the Python 3.7 dictionary. Things might change ...
        '''
        self.cnc_tools = {}

        '''
           This is a dict of dictionaries. Each dict is associated with a tool present in the file. The key is the 
           diameter of the tools and the value is another dict that will hold the data under the following form:
              {tooldia:   {
                          'tool': int,
                          'nr_drills': int,
                          'nr_slots': int,
                          'offset': float,
                          'data': {} # a dict to hold the parameters
                          'gcode': "" # a string with the actual GCODE
                          'gcode_parsed': {} # dictionary holding the CNCJob geometry and type of geometry (cut or move)
                          'solid_geometry': []
                          },
                          ...
              }
           It is populated in the FlatCAMExcellon.on_create_cncjob_click() but actually 
           it's done in camlib.Excellon.generate_from_excellon_by_tool()
           BEWARE: I rely on the ordered nature of the Python 3.7 dictionary. Things might change ...
       '''
        self.exc_cnc_tools = {}

        # flag to store if the CNCJob is part of a special group of CNCJob objects that can't be processed by the
        # default engine of FlatCAM. They generated by some of tools and are special cases of CNCJob objects.
        self. special_group = None

        # for now it show if the plot will be done for multi-tool CNCJob (True) or for single tool
        # (like the one in the TCL Command), False
        self.multitool = False

        # used for parsing the GCode lines to adjust the GCode when the GCode is offseted or scaled
        gcodex_re_string = r'(?=.*(X[-\+]?\d*\.\d*))'
        self.g_x_re = re.compile(gcodex_re_string)
        gcodey_re_string = r'(?=.*(Y[-\+]?\d*\.\d*))'
        self.g_y_re = re.compile(gcodey_re_string)
        gcodez_re_string = r'(?=.*(Z[-\+]?\d*\.\d*))'
        self.g_z_re = re.compile(gcodez_re_string)

        gcodef_re_string = r'(?=.*(F[-\+]?\d*\.\d*))'
        self.g_f_re = re.compile(gcodef_re_string)
        gcodet_re_string = r'(?=.*(\=\s*[-\+]?\d*\.\d*))'
        self.g_t_re = re.compile(gcodet_re_string)

        gcodenr_re_string = r'([+-]?\d*\.\d+)'
        self.g_nr_re = re.compile(gcodenr_re_string)

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from predecessors.
        self.ser_attrs += ['options', 'kind', 'cnc_tools', 'multitool']

        self.annotation = self.app.plotcanvas.new_text_group()

    def build_ui(self):
        self.ui_disconnect()

        FlatCAMObj.build_ui(self)

        # if the FlatCAM object is Excellon don't build the CNC Tools Table but hide it
        if self.cnc_tools:
            self.ui.cnc_tools_table.show()
        else:
            self.ui.cnc_tools_table.hide()


        offset = 0
        tool_idx = 0

        n = len(self.cnc_tools)
        self.ui.cnc_tools_table.setRowCount(n)

        for dia_key, dia_value in self.cnc_tools.items():

            tool_idx += 1
            row_no = tool_idx - 1

            id = QtWidgets.QTableWidgetItem('%d' % int(tool_idx))
            # id.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.ui.cnc_tools_table.setItem(row_no, 0, id)  # Tool name/id

            # Make sure that the tool diameter when in MM is with no more than 2 decimals.
            # There are no tool bits in MM with more than 2 decimals diameter.
            # For INCH the decimals should be no more than 4. There are no tools under 10mils.
            if self.units == 'MM':
                dia_item = QtWidgets.QTableWidgetItem('%.2f' % float(dia_value['tooldia']))
            else:
                dia_item = QtWidgets.QTableWidgetItem('%.4f' % float(dia_value['tooldia']))

            offset_txt = list(str(dia_value['offset']))
            offset_txt[0] = offset_txt[0].upper()
            offset_item = QtWidgets.QTableWidgetItem(''.join(offset_txt))
            type_item = QtWidgets.QTableWidgetItem(str(dia_value['type']))
            tool_type_item = QtWidgets.QTableWidgetItem(str(dia_value['tool_type']))

            id.setFlags(QtCore.Qt.ItemIsEnabled)
            dia_item.setFlags(QtCore.Qt.ItemIsEnabled)
            offset_item.setFlags(QtCore.Qt.ItemIsEnabled)
            type_item.setFlags(QtCore.Qt.ItemIsEnabled)
            tool_type_item.setFlags(QtCore.Qt.ItemIsEnabled)

            # hack so the checkbox stay centered in the table cell
            # used this:
            # https://stackoverflow.com/questions/32458111/pyqt-allign-checkbox-and-put-it-in-every-row
            # plot_item = QtWidgets.QWidget()
            # checkbox = FCCheckBox()
            # checkbox.setCheckState(QtCore.Qt.Checked)
            # qhboxlayout = QtWidgets.QHBoxLayout(plot_item)
            # qhboxlayout.addWidget(checkbox)
            # qhboxlayout.setAlignment(QtCore.Qt.AlignCenter)
            # qhboxlayout.setContentsMargins(0, 0, 0, 0)
            plot_item = FCCheckBox()
            plot_item.setLayoutDirection(QtCore.Qt.RightToLeft)
            tool_uid_item = QtWidgets.QTableWidgetItem(str(dia_key))
            if self.ui.plot_cb.isChecked():
                plot_item.setChecked(True)

            self.ui.cnc_tools_table.setItem(row_no, 1, dia_item)  # Diameter
            self.ui.cnc_tools_table.setItem(row_no, 2, offset_item)  # Offset
            self.ui.cnc_tools_table.setItem(row_no, 3, type_item)  # Toolpath Type
            self.ui.cnc_tools_table.setItem(row_no, 4, tool_type_item)  # Tool Type

            ### REMEMBER: THIS COLUMN IS HIDDEN IN OBJECTUI.PY ###
            self.ui.cnc_tools_table.setItem(row_no, 5, tool_uid_item)  # Tool unique ID)
            self.ui.cnc_tools_table.setCellWidget(row_no, 6, plot_item)

        # make the diameter column editable
        # for row in range(tool_idx):
        #     self.ui.cnc_tools_table.item(row, 1).setFlags(QtCore.Qt.ItemIsSelectable |
        #                                                   QtCore.Qt.ItemIsEnabled)

        for row in range(tool_idx):
            self.ui.cnc_tools_table.item(row, 0).setFlags(
                self.ui.cnc_tools_table.item(row, 0).flags() ^ QtCore.Qt.ItemIsSelectable)

        self.ui.cnc_tools_table.resizeColumnsToContents()
        self.ui.cnc_tools_table.resizeRowsToContents()

        vertical_header = self.ui.cnc_tools_table.verticalHeader()
        # vertical_header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        vertical_header.hide()
        self.ui.cnc_tools_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        horizontal_header = self.ui.cnc_tools_table.horizontalHeader()
        horizontal_header.setMinimumSectionSize(10)
        horizontal_header.setDefaultSectionSize(70)
        horizontal_header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        horizontal_header.resizeSection(0, 20)
        horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        horizontal_header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(4, QtWidgets.QHeaderView.Fixed)
        horizontal_header.resizeSection(4, 40)
        horizontal_header.setSectionResizeMode(6, QtWidgets.QHeaderView.Fixed)
        horizontal_header.resizeSection(4, 17)
        # horizontal_header.setStretchLastSection(True)
        self.ui.cnc_tools_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.ui.cnc_tools_table.setColumnWidth(0, 20)
        self.ui.cnc_tools_table.setColumnWidth(4, 40)
        self.ui.cnc_tools_table.setColumnWidth(6, 17)

        # self.ui.geo_tools_table.setSortingEnabled(True)

        self.ui.cnc_tools_table.setMinimumHeight(self.ui.cnc_tools_table.getHeight())
        self.ui.cnc_tools_table.setMaximumHeight(self.ui.cnc_tools_table.getHeight())

        self.ui_connect()

    def set_ui(self, ui):
        FlatCAMObj.set_ui(self, ui)

        FlatCAMApp.App.log.debug("FlatCAMCNCJob.set_ui()")

        assert isinstance(self.ui, CNCObjectUI), \
            "Expected a CNCObjectUI, got %s" % type(self.ui)

        # this signal has to be connected to it's slot before the defaults are populated
        # the decision done in the slot has to override the default value set bellow
        self.ui.toolchange_cb.toggled.connect(self.on_toolchange_custom_clicked)

        self.form_fields.update({
            "plot": self.ui.plot_cb,
            # "tooldia": self.ui.tooldia_entry,
            "append": self.ui.append_text,
            "prepend": self.ui.prepend_text,
            "toolchange_macro": self.ui.toolchange_text,
            "toolchange_macro_enable": self.ui.toolchange_cb
        })

        # Fill form fields only on object create
        self.to_form()

        # this means that the object that created this CNCJob was an Excellon
        try:
            if self.travel_distance:
                self.ui.t_distance_label.show()
                self.ui.t_distance_entry.setVisible(True)
                self.ui.t_distance_entry.setDisabled(True)
                self.ui.t_distance_entry.set_value('%.4f' % float(self.travel_distance))
                self.ui.units_label.setText(str(self.units).lower())
                self.ui.units_label.setDisabled(True)
        except AttributeError:
            pass

        # set the kind of geometries are plotted by default with plot2() from camlib.CNCJob
        self.ui.cncplot_method_combo.set_value(self.app.defaults["cncjob_plot_kind"])

        # Show/Hide Advanced Options
        if self.app.defaults["global_app_level"] == 'b':
            self.ui.level.setText(_(
                '<span style="color:green;"><b>Basic</b></span>'
            ))

            self.ui.cnc_frame.hide()
        else:
            self.ui.level.setText(_(
                '<span style="color:red;"><b>Advanced</b></span>'
            ))
            self.ui.cnc_frame.show()

        self.ui.updateplot_button.clicked.connect(self.on_updateplot_button_click)
        self.ui.export_gcode_button.clicked.connect(self.on_exportgcode_button_click)
        self.ui.modify_gcode_button.clicked.connect(self.on_modifygcode_button_click)

        self.ui.tc_variable_combo.currentIndexChanged[str].connect(self.on_cnc_custom_parameters)

        self.ui.cncplot_method_combo.activated_custom.connect(self.on_plot_kind_change)

    def on_cnc_custom_parameters(self, signal_text):
        if signal_text == 'Parameters':
            return
        else:
            self.ui.toolchange_text.insertPlainText('%%%s%%' % signal_text)

    def ui_connect(self):
        for row in range(self.ui.cnc_tools_table.rowCount()):
            self.ui.cnc_tools_table.cellWidget(row, 6).clicked.connect(self.on_plot_cb_click_table)
        self.ui.plot_cb.stateChanged.connect(self.on_plot_cb_click)

    def ui_disconnect(self):
        for row in range(self.ui.cnc_tools_table.rowCount()):
            self.ui.cnc_tools_table.cellWidget(row, 6).clicked.disconnect(self.on_plot_cb_click_table)
        try:
            self.ui.plot_cb.stateChanged.disconnect(self.on_plot_cb_click)
        except:
            pass

    def on_updateplot_button_click(self, *args):
        """
        Callback for the "Updata Plot" button. Reads the form for updates
        and plots the object.
        """
        self.read_form()
        self.plot()

    def on_plot_kind_change(self):
        kind = self.ui.cncplot_method_combo.get_value()
        self.plot(kind=kind)

    def on_exportgcode_button_click(self, *args):
        self.app.report_usage("cncjob_on_exportgcode_button")

        self.read_form()
        name = self.app.collection.get_active().options['name']

        if 'Roland' in self.pp_excellon_name or 'Roland' in self.pp_geometry_name:
            _filter_ = "RML1 Files (*.rol);;" \
                       "All Files (*.*)"
        elif 'hpgl' in self.pp_geometry_name:
            _filter_ = "HPGL Files (*.plt);;" \
                       "All Files (*.*)"
        else:
            _filter_ = "G-Code Files (*.nc);;G-Code Files (*.txt);;G-Code Files (*.tap);;G-Code Files (*.cnc);;" \
                       "G-Code Files (*.g-code);;All Files (*.*)"

        try:
            dir_file_to_save = self.app.get_last_save_folder() + '/' + str(name)
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(
                caption=_("Export Machine Code ..."),
                directory=dir_file_to_save,
                filter=_filter_
            )
        except TypeError:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(caption=_("Export Machine Code ..."), filter=_filter_)

        filename = str(filename)

        if filename == '':
            self.app.inform.emit(_(
                "[WARNING_NOTCL]Export Machine Code cancelled ..."))
            return

        preamble = str(self.ui.prepend_text.get_value())
        postamble = str(self.ui.append_text.get_value())

        gc = self.export_gcode(filename, preamble=preamble, postamble=postamble)
        if gc == 'fail':
            return

        self.app.file_saved.emit("gcode", filename)
        self.app.inform.emit(_("[success] Machine Code file saved to: %s") % filename)

    def on_modifygcode_button_click(self, *args):
        preamble = str(self.ui.prepend_text.get_value())
        postamble = str(self.ui.append_text.get_value())
        gc = self.export_gcode(preamble=preamble, postamble=postamble, to_file=True)
        if gc == 'fail':
            return
        else:
            self.app.gcode_edited = gc

        # add the tab if it was closed
        self.app.ui.plot_tab_area.addTab(self.app.ui.cncjob_tab, _("Code Editor"))

        # delete the absolute and relative position and messages in the infobar
        self.app.ui.position_label.setText("")
        self.app.ui.rel_position_label.setText("")

        # Switch plot_area to CNCJob tab
        self.app.ui.plot_tab_area.setCurrentWidget(self.app.ui.cncjob_tab)

        # first clear previous text in text editor (if any)
        self.app.ui.code_editor.clear()

        # then append the text from GCode to the text editor
        try:
            for line in self.app.gcode_edited:
                proc_line = str(line).strip('\n')
                self.app.ui.code_editor.append(proc_line)
        except Exception as e:
            log.debug('FlatCAMCNNJob.on_modifygcode_button_click() -->%s' % str(e))
            self.app.inform.emit(_('[ERROR]FlatCAMCNNJob.on_modifygcode_button_click() -->%s') % str(e))
            return

        self.app.ui.code_editor.moveCursor(QtGui.QTextCursor.Start)

        self.app.handleTextChanged()
        self.app.ui.show()

    def gcode_header(self):
        log.debug("FlatCAMCNCJob.gcode_header()")
        time_str = "{:%A, %d %B %Y at %H:%M}".format(datetime.now())
        marlin = False
        hpgl = False
        probe_pp = False

        try:
            for key in self.cnc_tools:
                ppg = self.cnc_tools[key]['data']['ppname_g']
                if ppg == 'marlin' or ppg == 'Repetier':
                    marlin = True
                    break
                if ppg == 'hpgl':
                    hpgl = True
                    break
                if "toolchange_probe" in ppg.lower():
                    probe_pp = True
                    break
        except Exception as e:
            log.debug("FlatCAMCNCJob.gcode_header() error: --> %s" % str(e))

        try:
            if self.options['ppname_e'] == 'marlin' or self.options['ppname_e'] == 'Repetier':
                marlin = True
        except Exception as e:
            log.debug("FlatCAMCNCJob.gcode_header(): --> There is no such self.option: %s" % str(e))

        try:
            if "toolchange_probe" in self.options['ppname_e'].lower():
                probe_pp = True
        except Exception as e:
            log.debug("FlatCAMCNCJob.gcode_header(): --> There is no such self.option: %s" % str(e))

        if marlin is True:
            gcode = ';Marlin(Repetier) G-CODE GENERATED BY FLATCAM v%s - www.flatcam.org - Version Date:    %s\n' % \
                    (str(self.app.version), str(self.app.version_date)) + '\n'

            gcode += ';Name: ' + str(self.options['name']) + '\n'
            gcode += ';Type: ' + "G-code from " + str(self.options['type']) + '\n'

            # if str(p['options']['type']) == 'Excellon' or str(p['options']['type']) == 'Excellon Geometry':
            #     gcode += '(Tools in use: ' + str(p['options']['Tools_in_use']) + ')\n'

            gcode += ';Units: ' + self.units.upper() + '\n' + "\n"
            gcode += ';Created on ' + time_str + '\n' + '\n'
        elif hpgl is True:
            gcode = 'CO "HPGL CODE GENERATED BY FLATCAM v%s - www.flatcam.org - Version Date:    %s' % \
                    (str(self.app.version), str(self.app.version_date)) + '";\n'

            gcode += 'CO "Name: ' + str(self.options['name']) + '";\n'
            gcode += 'CO "Type: ' + "HPGL code from " + str(self.options['type']) + '";\n'

            # if str(p['options']['type']) == 'Excellon' or str(p['options']['type']) == 'Excellon Geometry':
            #     gcode += '(Tools in use: ' + str(p['options']['Tools_in_use']) + ')\n'

            gcode += 'CO "Units: ' + self.units.upper() + '";\n'
            gcode += 'CO "Created on ' + time_str + '";\n'
        elif probe_pp is True:
            gcode = '(G-CODE GENERATED BY FLATCAM v%s - www.flatcam.org - Version Date: %s)\n' % \
                    (str(self.app.version), str(self.app.version_date)) + '\n'

            gcode += '(This GCode tool change is done by using a Probe.)\n' \
                     '(Make sure that before you start the job you first do a rough zero for Z axis.)\n' \
                     '(This means that you need to zero the CNC axis and then jog to the toolchange X, Y location,)\n' \
                     '(mount the probe and adjust the Z so more or less the probe tip touch the plate. ' \
                     'Then zero the Z axis.)\n' + '\n'

            gcode += '(Name: ' + str(self.options['name']) + ')\n'
            gcode += '(Type: ' + "G-code from " + str(self.options['type']) + ')\n'

            # if str(p['options']['type']) == 'Excellon' or str(p['options']['type']) == 'Excellon Geometry':
            #     gcode += '(Tools in use: ' + str(p['options']['Tools_in_use']) + ')\n'

            gcode += '(Units: ' + self.units.upper() + ')\n' + "\n"
            gcode += '(Created on ' + time_str + ')\n' + '\n'
        else:
            gcode = '(G-CODE GENERATED BY FLATCAM v%s - www.flatcam.org - Version Date: %s)\n' % \
                    (str(self.app.version), str(self.app.version_date)) + '\n'

            gcode += '(Name: ' + str(self.options['name']) + ')\n'
            gcode += '(Type: ' + "G-code from " + str(self.options['type']) + ')\n'

            # if str(p['options']['type']) == 'Excellon' or str(p['options']['type']) == 'Excellon Geometry':
            #     gcode += '(Tools in use: ' + str(p['options']['Tools_in_use']) + ')\n'

            gcode += '(Units: ' + self.units.upper() + ')\n' + "\n"
            gcode += '(Created on ' + time_str + ')\n' + '\n'

        return gcode

    def export_gcode(self, filename=None, preamble='', postamble='', to_file=False):
        gcode = ''
        roland = False
        hpgl = False

        try:
            if self.special_group:
                self.app.inform.emit(_("[WARNING_NOTCL]This CNCJob object can't be processed because "
                                     "it is a %s CNCJob object.") % str(self.special_group))
                return 'fail'
        except AttributeError:
            pass

        # detect if using Roland postprocessor
        try:
            for key in self.cnc_tools:
                if self.cnc_tools[key]['data']['ppname_g'] == 'Roland_MDX_20':
                    roland = True
                    break
                if self.cnc_tools[key]['data']['ppname_g'] == 'hpgl':
                    hpgl = True
                    break
        except:
            try:
                for key in self.cnc_tools:
                    if self.cnc_tools[key]['data']['ppname_e'] == 'Roland_MDX_20':
                        roland = True
                        break
            except:
                pass

        # do not add gcode_header when using the Roland postprocessor, add it for every other postprocessor
        if roland is False and hpgl is False:
            gcode = self.gcode_header()

        # detect if using multi-tool and make the Gcode summation correctly for each case
        if self.multitool is True:
            for tooluid_key in self.cnc_tools:
                for key, value in self.cnc_tools[tooluid_key].items():
                    if key == 'gcode':
                        gcode += value
                        break
        else:
            gcode += self.gcode

        if roland is True:
            g = preamble + gcode + postamble
        elif hpgl is True:
            g = self.gcode_header() + preamble + gcode + postamble
        else:
            # fix so the preamble gets inserted in between the comments header and the actual start of GCODE
            g_idx = gcode.rfind('G20')

            # if it did not find 'G20' then search for 'G21'
            if g_idx == -1:
                g_idx = gcode.rfind('G21')

            # if it did not find 'G20' and it did not find 'G21' then there is an error and return
            if g_idx == -1:
                self.app.inform.emit(_(
                    "[ERROR_NOTCL] G-code does not have a units code: either G20 or G21"
                ))
                return

            g = gcode[:g_idx] + preamble + '\n' + gcode[g_idx:] + postamble

        # if toolchange custom is used, replace M6 code with the code from the Toolchange Custom Text box
        if self.ui.toolchange_cb.get_value() is True:
            # match = self.re_toolchange.search(g)
            if 'M6' in g:
                m6_code = self.parse_custom_toolchange_code(self.ui.toolchange_text.get_value())
                if m6_code is None or m6_code == '':
                    self.app.inform.emit(_(
                        "[ERROR_NOTCL] Cancelled. The Toolchange Custom code is enabled "
                        "but it's empty."
                    ))
                    return 'fail'

                g = g.replace('M6', m6_code)
                self.app.inform.emit(_(
                    "[success] Toolchange G-code was replaced by a custom code."
                ))

        # lines = StringIO(self.gcode)
        lines = StringIO(g)

        ## Write
        if filename is not None:
            try:
                with open(filename, 'w') as f:
                    for line in lines:
                        f.write(line)

            except FileNotFoundError:
                self.app.inform.emit(_(
                    "[WARNING_NOTCL] No such file or directory"
                ))
                return
        elif to_file is False:
            # Just for adding it to the recent files list.
            self.app.file_opened.emit("cncjob", filename)
            self.app.file_saved.emit("cncjob", filename)

            self.app.inform.emit("[success] Saved to: " + filename)
        else:
            return lines

    def on_toolchange_custom_clicked(self, signal):
        try:
            if 'toolchange_custom' not in str(self.options['ppname_e']).lower():
                print(self.options['ppname_e'])
                if self.ui.toolchange_cb.get_value():
                    self.ui.toolchange_cb.set_value(False)
                    self.app.inform.emit(
                        _(
                            "[WARNING_NOTCL] The used postprocessor file has to have in it's name: 'toolchange_custom'"
                        ))
        except KeyError:
            try:
                for key in self.cnc_tools:
                    ppg = self.cnc_tools[key]['data']['ppname_g']
                    if 'toolchange_custom' not in str(ppg).lower():
                        print(ppg)
                        if self.ui.toolchange_cb.get_value():
                            self.ui.toolchange_cb.set_value(False)
                            self.app.inform.emit(
                                _(
                                    "[WARNING_NOTCL] The used postprocessor file has to have in it's name: "
                                    "'toolchange_custom'"
                                ))
            except KeyError:
                self.app.inform.emit(
                    _(
                        "[ERROR] There is no postprocessor file."
                    ))

    def get_gcode(self, preamble='', postamble=''):
        #we need this to be able get_gcode separatelly for shell command export_gcode
        return preamble + '\n' + self.gcode + "\n" + postamble

    def get_svg(self):
        # we need this to be able get_svg separately for shell command export_svg
        pass

    def on_plot_cb_click(self, *args):
        if self.muted_ui:
            return
        kind = self.ui.cncplot_method_combo.get_value()
        self.plot(kind=kind)
        self.read_form_item('plot')

        self.ui_disconnect()
        cb_flag = self.ui.plot_cb.isChecked()
        for row in range(self.ui.cnc_tools_table.rowCount()):
            table_cb = self.ui.cnc_tools_table.cellWidget(row, 6)
            if cb_flag:
                table_cb.setChecked(True)
            else:
                table_cb.setChecked(False)
        self.ui_connect()

    def on_plot_cb_click_table(self):
        # self.ui.cnc_tools_table.cellWidget(row, 2).widget().setCheckState(QtCore.Qt.Unchecked)
        self.ui_disconnect()
        cw = self.sender()
        cw_index = self.ui.cnc_tools_table.indexAt(cw.pos())
        cw_row = cw_index.row()

        kind = self.ui.cncplot_method_combo.get_value()

        self.shapes.clear(update=True)

        for tooluid_key in self.cnc_tools:
            tooldia = float('%.4f' % float(self.cnc_tools[tooluid_key]['tooldia']))
            gcode_parsed = self.cnc_tools[tooluid_key]['gcode_parsed']
            # tool_uid = int(self.ui.cnc_tools_table.item(cw_row, 3).text())

            for r in range(self.ui.cnc_tools_table.rowCount()):
                if int(self.ui.cnc_tools_table.item(r, 5).text()) == int(tooluid_key):
                    if self.ui.cnc_tools_table.cellWidget(r, 6).isChecked():
                        self.plot2(tooldia=tooldia, obj=self, visible=True, gcode_parsed=gcode_parsed, kind=kind)

        self.shapes.redraw()

        # make sure that the general plot is disabled if one of the row plot's are disabled and
        # if all the row plot's are enabled also enable the general plot checkbox
        cb_cnt = 0
        total_row = self.ui.cnc_tools_table.rowCount()
        for row in range(total_row):
            if self.ui.cnc_tools_table.cellWidget(row, 6).isChecked():
                cb_cnt += 1
            else:
                cb_cnt -= 1
        if cb_cnt < total_row:
            self.ui.plot_cb.setChecked(False)
        else:
            self.ui.plot_cb.setChecked(True)
        self.ui_connect()


    def plot(self, visible=None, kind='all'):

        # Does all the required setup and returns False
        # if the 'ptint' option is set to False.
        if not FlatCAMObj.plot(self):
            return

        visible = visible if visible else self.options['plot']

        try:
            if self.multitool is False: # single tool usage
                self.plot2(tooldia=float(self.options["tooldia"]), obj=self, visible=visible, kind=kind)
            else:
                # multiple tools usage
                for tooluid_key in self.cnc_tools:
                    tooldia = float('%.4f' % float(self.cnc_tools[tooluid_key]['tooldia']))
                    gcode_parsed = self.cnc_tools[tooluid_key]['gcode_parsed']
                    self.plot2(tooldia=tooldia, obj=self, visible=visible, gcode_parsed=gcode_parsed, kind=kind)
            self.shapes.redraw()
        except (ObjectDeleted, AttributeError):
            self.shapes.clear(update=True)
            self.annotation.clear(update=True)

    def convert_units(self, units):
        factor = CNCjob.convert_units(self, units)
        FlatCAMApp.App.log.debug("FlatCAMCNCjob.convert_units()")
        self.options["tooldia"] = float(self.options["tooldia"]) * factor

        param_list = ['cutz', 'depthperpass', 'travelz', 'feedrate', 'feedrate_z', 'feedrate_rapid',
                      'endz', 'toolchangez']

        temp_tools_dict = {}
        tool_dia_copy = {}
        data_copy = {}

        for tooluid_key, tooluid_value in self.cnc_tools.items():
            for dia_key, dia_value in tooluid_value.items():
                if dia_key == 'tooldia':
                    dia_value *= factor
                    dia_value = float('%.4f' % dia_value)
                    tool_dia_copy[dia_key] = dia_value
                if dia_key == 'offset':
                    tool_dia_copy[dia_key] = dia_value
                if dia_key == 'offset_value':
                    dia_value *= factor
                    tool_dia_copy[dia_key] = dia_value

                if dia_key == 'type':
                    tool_dia_copy[dia_key] = dia_value
                if dia_key == 'tool_type':
                    tool_dia_copy[dia_key] = dia_value
                if dia_key == 'data':
                    for data_key, data_value in dia_value.items():
                        # convert the form fields that are convertible
                        for param in param_list:
                            if data_key == param and data_value is not None:
                                data_copy[data_key] = data_value * factor
                        # copy the other dict entries that are not convertible
                        if data_key not in param_list:
                            data_copy[data_key] = data_value
                    tool_dia_copy[dia_key] = deepcopy(data_copy)
                    data_copy.clear()

                if dia_key == 'gcode':
                    tool_dia_copy[dia_key] = dia_value
                if dia_key == 'gcode_parsed':
                    tool_dia_copy[dia_key] = dia_value
                if dia_key == 'solid_geometry':
                    tool_dia_copy[dia_key] = dia_value

                # if dia_key == 'solid_geometry':
                #     tool_dia_copy[dia_key] = affinity.scale(dia_value, xfact=factor, origin=(0, 0))
                # if dia_key == 'gcode_parsed':
                #     for g in dia_value:
                #         g['geom'] = affinity.scale(g['geom'], factor, factor, origin=(0, 0))
                #
                #     tool_dia_copy['gcode_parsed'] = deepcopy(dia_value)
                #     tool_dia_copy['solid_geometry'] = cascaded_union([geo['geom'] for geo in dia_value])

            temp_tools_dict.update({
                tooluid_key: deepcopy(tool_dia_copy)
            })
            tool_dia_copy.clear()

        self.cnc_tools.clear()
        self.cnc_tools = deepcopy(temp_tools_dict)

# end of file
