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
import shapely.affinity as affinity

from copy import deepcopy
from copy import copy

from io import StringIO
import traceback
import inspect  # TODO: For debugging only.
from datetime import datetime

from flatcamEditors.FlatCAMTextEditor import TextEditor
from flatcamGUI.ObjectUI import *
from FlatCAMCommon import LoudDict
from flatcamGUI.PlotCanvasLegacy import ShapeCollectionLegacy
from flatcamParsers.ParseExcellon import Excellon
from flatcamParsers.ParseGerber import Gerber
from camlib import Geometry, CNCjob
import FlatCAMApp

from flatcamGUI.VisPyVisuals import ShapeCollection

import tkinter as tk
import os, sys, itertools
import ezdxf

import math
import numpy as np

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


# Interrupts plotting process if FlatCAMObj has been deleted
class ObjectDeleted(Exception):
    pass


class ValidationError(Exception):
    def __init__(self, message, errors):
        super().__init__(message)

        self.errors = errors

# #######################################
# #            FlatCAMObj              ##
# #######################################


class FlatCAMObj(QtCore.QObject):
    """
    Base type of objects handled in FlatCAM. These become interactive
    in the GUI, can be plotted, and their options can be modified
    by the user in their respective forms.
    """

    # Instance of the application to which these are related.
    # The app should set this value.
    app = None

    # signal to plot a single object
    plot_single_object = QtCore.pyqtSignal()

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

        # store here the default data for Geometry Data
        self.default_data = {}

        # 2D mode
        # Axes must exist and be attached to canvas.
        self.axes = None
        self.kind = None  # Override with proper name

        if self.app.is_legacy is False:
            self.shapes = self.app.plotcanvas.new_shape_group()
            # self.shapes = ShapeCollection(parent=self.app.plotcanvas.view.scene, pool=self.app.pool, layers=2)
        else:
            self.shapes = ShapeCollectionLegacy(obj=self, app=self.app, name=name)

        self.mark_shapes = dict()

        self.item = None  # Link with project view item

        self.muted_ui = False
        self.deleted = False

        try:
            self._drawing_tolerance = float(self.app.defaults["global_tolerance"]) if \
                self.app.defaults["global_tolerance"] else 0.01
        except ValueError:
            self._drawing_tolerance = 0.01

        self.isHovering = False
        self.notHovering = True

        # Flag to show if a selection shape is drawn
        self.selection_shape_drawn = False

        # self.units = 'IN'
        self.units = self.app.defaults['units']

        self.plot_single_object.connect(self.single_object_plot)

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
                    log.debug("FlatCAMObj.from_dict() --> KeyError: %s. "
                              "Means that we are loading an old project that don't"
                              "have all attributes in the latest FlatCAM." % str(attr))
                    pass

    def on_options_change(self, key):
        # Update form on programmatically options change
        self.set_form_item(key)

        # Set object visibility
        if key == 'plot':
            self.visible = self.options['plot']

        self.optionChanged.emit(key)

    def set_ui(self, ui):
        self.ui = ui

        self.form_fields = {"name": self.ui.name_entry}

        assert isinstance(self.ui, ObjectUI)
        self.ui.name_entry.returnPressed.connect(self.on_name_activate)

        try:
            # it will raise an exception for those FlatCAM objects that do not build UI with the common elements
            self.ui.offset_button.clicked.connect(self.on_offset_button_click)
        except (TypeError, AttributeError):
            pass

        try:
            self.ui.scale_button.clicked.connect(self.on_scale_button_click)
        except (TypeError, AttributeError):
            pass

        try:
            self.ui.offsetvector_entry.returnPressed.connect(self.on_offset_button_click)
        except (TypeError, AttributeError):
            pass

        # Creates problems on focusOut
        try:
            self.ui.scale_entry.returnPressed.connect(self.on_scale_button_click)
        except (TypeError, AttributeError):
            pass

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

        try:
            # HACK: disconnect the scale entry signal since on focus out event will trigger an undesired scale()
            # it seems that the takewidget() does generate a focus out event for the QDoubleSpinbox ...
            # and reconnect after the takeWidget() is done
            # self.ui.scale_entry.returnPressed.disconnect(self.on_scale_button_click)
            self.app.ui.selected_scroll_area.takeWidget()
            # self.ui.scale_entry.returnPressed.connect(self.on_scale_button_click)
        except Exception as e:
            self.app.log.debug("FlatCAMObj.build_ui() --> Nothing to remove: %s" % str(e))
        self.app.ui.selected_scroll_area.setWidget(self.ui)

        self.muted_ui = False

    def on_name_activate(self, silent=None):
        old_name = copy(self.options["name"])
        new_name = self.ui.name_entry.get_value()

        if new_name != old_name:
            # update the SHELL auto-completer model data
            try:
                self.app.myKeywords.remove(old_name)
                self.app.myKeywords.append(new_name)
                self.app.shell._edit.set_model_data(self.app.myKeywords)
                self.app.ui.code_editor.set_model_data(self.app.myKeywords)
            except Exception as e:
                log.debug("on_name_activate() --> Could not remove the old object name from auto-completer model list")

            self.options["name"] = self.ui.name_entry.get_value()
            self.default_data["name"] = self.ui.name_entry.get_value()
            self.app.collection.update_view()
            if silent:
                self.app.inform.emit('[success] %s: %s %s: %s' % (
                    _("Name changed from"), str(old_name), _("to"), str(new_name)
                )
                                     )

    def on_offset_button_click(self):
        self.app.report_usage("obj_on_offset_button")

        self.read_form()
        vector_val = self.ui.offsetvector_entry.get_value()

        def worker_task():
            with self.app.proc_container.new(_("Offsetting...")):
                self.offset(vector_val)
            self.app.proc_container.update_view_text('')
            with self.app.proc_container.new('%s...' % _("Plotting")):
                self.plot()
            self.app.object_changed.emit(self)

        self.app.worker_task.emit({'fcn': worker_task, 'params': []})

    def on_scale_button_click(self):
        self.read_form()
        try:
            factor = float(eval(self.ui.scale_entry.get_value()))
        except Exception as e:
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Scaling could not be executed."))
            log.debug("FlatCAMObj.on_scale_button_click() -- %s" % str(e))
            return

        if type(factor) != float:
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Scaling could not be executed."))

        # if factor is 1.0 do nothing, there is no point in scaling with a factor of 1.0
        if factor == 1.0:
            self.app.inform.emit('[success] %s' % _("Scale done."))
            return

        log.debug("FlatCAMObj.on_scale_button_click()")

        def worker_task():
            with self.app.proc_container.new(_("Scaling...")):
                self.scale(factor)
                self.app.inform.emit('[success] %s' % _("Scale done."))

            self.app.proc_container.update_view_text('')
            with self.app.proc_container.new('%s...' % _("Plotting")):
                self.plot()
            self.app.object_changed.emit(self)

        self.app.worker_task.emit({'fcn': worker_task, 'params': []})

    def on_skew_button_click(self):
        self.app.report_usage("obj_on_skew_button")
        self.read_form()
        x_angle = self.ui.xangle_entry.get_value()
        y_angle = self.ui.yangle_entry.get_value()

        def worker_task():
            with self.app.proc_container.new(_("Skewing...")):
                self.skew(x_angle, y_angle)
            self.app.proc_container.update_view_text('')
            with self.app.proc_container.new('%s...' % _("Plotting")):
                self.plot()
            self.app.object_changed.emit(self)

        self.app.worker_task.emit({'fcn': worker_task, 'params': []})

    def to_form(self):
        """
        Copies options to the UI form.

        :return: None
        """
        FlatCAMApp.App.log.debug(str(inspect.stack()[1][3]) + " --> FlatCAMObj.to_form()")
        for option in self.options:
            try:
                self.set_form_item(option)
            except Exception:
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
            except Exception:
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
            pass
            # self.app.log.warning("Failed to read option from field: %s" % option)

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

    def single_object_plot(self):
        def plot_task():
            with self.app.proc_container.new('%s...' % _("Plotting")):
                self.plot()
            self.app.object_changed.emit(self)

        self.app.worker_task.emit({'fcn': plot_task, 'params': []})

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

    def add_mark_shape(self, apid, **kwargs):
        if self.deleted:
            raise ObjectDeleted()
        else:
            key = self.mark_shapes[apid].add(tolerance=self.drawing_tolerance, layer=0, **kwargs)
        return key

    def update_filters(self, last_ext, filter_string):
        """
        Will modify the filter string that is used when saving a file (a list of file extensions) to have the last
        used file extension as the first one in the special string

        :param last_ext: the file extension that was last used to save a file
        :param filter_string: a key in self.app.defaults that holds a string with the filter from QFileDialog
        used when saving a file
        :return: None
        """

        filters = copy(self.app.defaults[filter_string])
        filter_list = filters.split(';;')
        filter_list_enum_1 = enumerate(filter_list)

        # search for the last element in the filters which should always be "All Files (*.*)"
        last_elem = ''
        for elem in list(filter_list_enum_1):
            if '(*.*)' in elem[1]:
                last_elem = filter_list.pop(elem[0])

        filter_list_enum = enumerate(filter_list)
        for elem in list(filter_list_enum):
            if '.' + last_ext in elem[1]:
                used_ext = filter_list.pop(elem[0])

                # sort the extensions back
                filter_list.sort(key=lambda x: x.rpartition('.')[2])

                # add as a first element the last used extension
                filter_list.insert(0, used_ext)
                # add back the element that should always be the last (All Files)
                filter_list.append(last_elem)

                self.app.defaults[filter_string] = ';;'.join(filter_list)
                return

    @staticmethod
    def poly2rings(poly):
        return [poly.exterior] + [interior for interior in poly.interiors]

    @property
    def visible(self):
        return self.shapes.visible

    @visible.setter
    def visible(self, value, threaded=True):
        log.debug("FlatCAMObj.visible()")

        def worker_task(app_obj):
            self.shapes.visible = value

            if self.app.is_legacy is False:
                # Not all object types has annotations
                try:
                    self.annotation.visible = value
                except Exception as e:
                    pass

        if threaded is False:
            worker_task(app_obj=self.app)
        else:
            self.app.worker_task.emit({'fcn': worker_task, 'params': [self]})

    @property
    def drawing_tolerance(self):
        self.units = self.app.defaults['units'].upper()
        tol = self._drawing_tolerance if self.units == 'MM' or not self.units else self._drawing_tolerance / 25.4
        return tol

    @drawing_tolerance.setter
    def drawing_tolerance(self, value):
        self.units = self.app.defaults['units'].upper()
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

    def merge(self, grb_list, grb_final):
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
        self.poly_dict = dict()

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
        FlatCAMApp.App.log.debug("FlatCAMGerber.set_ui()")

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
        self.ui.obj_combo.setCurrentIndex(1)
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
        except Exception as e:
            return
        try:
            dang = float(self.ui.tipangle_spinner.get_value())
        except Exception as e:
            return
        try:
            cutz = float(self.ui.cutz_spinner.get_value())
        except Exception as e:
            return

        cutz *= -1
        if cutz < 0:
            cutz *= -1

        half_tip_angle = dang / 2

        tool_diameter = tdia + (2 * cutz * math.tan(math.radians(half_tip_angle)))
        self.ui.iso_tool_dia_entry.set_value(tool_diameter)

    def on_type_obj_index_changed(self, index):
        obj_type = self.ui.type_obj_combo.currentIndex()
        self.ui.obj_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.ui.obj_combo.setCurrentIndex(0)

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
        self.app.report_usage("gerber_on_generatenoncopper_button")

        self.read_form()
        name = self.options["name"] + "_noncopper"

        def geo_init(geo_obj, app_obj):
            assert isinstance(geo_obj, FlatCAMGeometry)
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

        self.app.new_object("geometry", name, geo_init)

    def on_generatebb_button_click(self, *args):
        self.app.report_usage("gerber_on_generatebb_button")
        self.read_form()
        name = self.options["name"] + "_bbox"

        def geo_init(geo_obj, app_obj):
            assert isinstance(geo_obj, FlatCAMGeometry)

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

        self.app.new_object("geometry", name, geo_init)

    def on_iso_button_click(self, *args):

        obj = self.app.collection.get_active()

        self.iso_type = 2
        if self.ui.iso_type_radio.get_value() == 'ext':
            self.iso_type = 0
        if self.ui.iso_type_radio.get_value() == 'int':
            self.iso_type = 1

        def worker_task(obj, app_obj):
            with self.app.proc_container.new(_("Isolating...")):
                if self.ui.follow_cb.get_value() is True:
                    obj.follow_geo()
                    # in the end toggle the visibility of the origin object so we can see the generated Geometry
                    obj.ui.plot_cb.toggle()
                else:
                    app_obj.report_usage("gerber_on_iso_button")
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
            self.app.new_object("geometry", follow_name, follow_init)
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

                geo_obj.solid_geometry = list()

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

                geo_obj.tools = dict()
                geo_obj.tools['1'] = dict()
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

                for i in range(passes):
                    iso_offset = dia * ((2 * i + 1) / 2.0) - (i * overlap * dia)

                    # if milling type is climb then the move is counter-clockwise around features
                    mill_dir = 1 if milling_type == 'cl' else 0
                    geom = self.generate_envelope(iso_offset, mill_dir, geometry=work_geo, env_iso_type=iso_t,
                                                  follow=follow, nr_passes=i)

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
            self.app.new_object("geometry", iso_name, iso_init, plot=plot)
        else:
            for i in range(passes):

                offset = dia * ((2 * i + 1) / 2.0) - (i * overlap * dia)
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

                def iso_init(geo_obj, app_obj):
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
                        app_obj.inform.emit('[ERROR_NOTCL] %s' % _("Isolation geometry could not be generated."))
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

                    geo_obj.tools = dict()
                    geo_obj.tools['1'] = dict()
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
                        app_obj.inform.emit('[success] %s: %s' %
                                            (_("Isolation geometry created"), geo_obj.options["name"]))
                    geo_obj.multigeo = False

                    # ############################################################
                    # ########## AREA SUBTRACTION ################################
                    # ############################################################
                    if self.ui.except_cb.get_value():
                        self.app.proc_container.update_view_text(' %s' % _("Subtracting Geo"))
                        geo_obj.solid_geometry = self.area_subtraction(geo_obj.solid_geometry)

                # TODO: Do something if this is None. Offer changing name?
                self.app.new_object("geometry", iso_name, iso_init, plot=plot)

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
                log.debug('FlatCAMGerber.isolate().generate_envelope() --> %s' % str(e))
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
                    log.debug("FlatCAMGerber.isolate().generate_envelope() Error --> Unexpected Geometry %s" %
                              type(geom))
            except Exception as e:
                log.debug("FlatCAMGerber.isolate().generate_envelope() Error --> %s" % str(e))
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
                log.debug(" FlatCAMGerber.on_aperture_visibility_changed() --> %s" % str(e))

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

        log.debug("FlatCAMObj.FlatCAMGerber.convert_units()")

        factor = Gerber.convert_units(self, units)

        # self.options['isotooldia'] = float(self.options['isotooldia']) * factor
        # self.options['bboxmargin'] = float(self.options['bboxmargin']) * factor

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
            log.debug("FlatCAMGerber.plot() --> %s" % str(e))

    # experimental plot() when the solid_geometry is stored in the self.apertures
    def plot_aperture(self, run_thread=True, **kwargs):
        """

        :param run_thread: if True run the aperture plot as a thread in a worker
        :param kwargs: color and face_color
        :return:
        """

        FlatCAMApp.App.log.debug(str(inspect.stack()[1][3]) + " --> FlatCAMGerber.plot_aperture()")

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
                    log.debug("FlatCAMGerber.plot_aperture() --> %s" % str(e))

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
                        log.debug("FlatCAMGerber.clear_plot_apertures() 'all' --> %s" % str(e))
            else:
                try:
                    if self.app.is_legacy is True:
                        self.mark_shapes[aperture].clear(update=False)
                    else:
                        self.mark_shapes[aperture].clear(update=True)
                except Exception as e:
                    log.debug("FlatCAMGerber.clear_plot_apertures() 'aperture' --> %s" % str(e))

    def clear_mark_all(self):
        self.ui.mark_all_cb.set_value(False)
        self.marked_rows[:] = []

    def on_mark_cb_click_table(self):
        """
        Will mark aperture geometries on canvas or delete the markings depending on the checkbox state
        :return:
        """

        self.ui_disconnect()
        cw = self.sender()
        try:
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
        log.debug("FlatCAMGerber.export_gerber() --> Generating the Gerber code from the selected Gerber file")

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

            for apid in self.apertures:
                if apid == '0':
                    continue
                else:
                    gerber_code += 'D%s*\n' % str(apid)
                    if 'geometry' in self.apertures[apid]:
                        for geo_elem in self.apertures[apid]['geometry']:
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
            log.debug("FlatCAMObj.FlatCAMGerber.export_gerber() --> %s" % str(e))

        if not self.apertures:
            log.debug("FlatCAMObj.FlatCAMGerber.export_gerber() --> Gerber Object is empty: no apertures.")
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


class FlatCAMExcellon(FlatCAMObj, Excellon):
    """
    Represents Excellon/Drill code.
    """

    ui_type = ExcellonObjectUI
    optionChanged = QtCore.pyqtSignal(str)

    def __init__(self, name):
        self.decimals = self.app.decimals

        self.circle_steps = int(self.app.defaults["geometry_circle_steps"])

        Excellon.__init__(self, geo_steps_per_circle=self.circle_steps)
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
            "spindlespeed": 0,
            "dwell": True,
            "dwelltime": 1000,
            "ppname_e": 'defaults',
            "z_pdepth": -0.02,
            "feedrate_probe": 3.0,
            "optimization_type": "R",
            "gcode_type": "drills"
        })

        # TODO: Document this.
        self.tool_cbs = dict()

        # dict to hold the tool number as key and tool offset as value
        self.tool_offset = dict()

        # default set of data to be added to each tool in self.tools as self.tools[tool]['data'] = self.default_data
        self.default_data = dict()

        # fill in self.default_data values from self.options
        for opt_key, opt_val in self.app.options.items():
            if opt_key.find('excellon_') == 0:
                self.default_data[opt_key] = deepcopy(opt_val)
        for opt_key, opt_val in self.app.options.items():
            if opt_key.find('geometry_') == 0:
                self.default_data[opt_key] = deepcopy(opt_val)

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

        self.multigeo = False
        self.units_found = self.app.defaults['units']

        self.fill_color = self.app.defaults['excellon_plot_fill']
        self.outline_color = self.app.defaults['excellon_plot_line']
        self.alpha_level = 'bf'

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from predecessors.
        self.ser_attrs += ['options', 'kind',]

    def merge(self, exc_list, exc_final):
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

        try:
            decimals_exc = self.decimals
        except AttributeError:
            decimals_exc = 4

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
                    except Exception as e:
                        exc.app.log.warning("Failed to copy option.", option)

            for drill in exc.drills:
                exc_tool_dia = float('%.*f' % (decimals_exc, exc.tools[drill['tool']]['C']))

                if exc_tool_dia not in custom_dict_drills:
                    custom_dict_drills[exc_tool_dia] = [drill['point']]
                else:
                    custom_dict_drills[exc_tool_dia].append(drill['point'])

            for slot in exc.slots:
                exc_tool_dia = float('%.*f' % (decimals_exc, exc.tools[slot['tool']]['C']))

                if exc_tool_dia not in custom_dict_slots:
                    custom_dict_slots[exc_tool_dia] = [[slot['start'], slot['stop']]]
                else:
                    custom_dict_slots[exc_tool_dia].append([slot['start'], slot['stop']])

            # add the zeros and units to the exc_final object
            exc_final.zeros = exc.zeros
            exc_final.units = exc.units

        # ##########################################
        # Here we add data to the exc_final object #
        # ##########################################

        # variable to make tool_name for the tools
        current_tool = 0
        # The tools diameter are now the keys in the drill_dia dict and the values are the Shapely Points in case of
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

        # The tools diameter are now the keys in the drill_dia dict and the values are a list ([start, stop])
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
                    exc_tool_dia = float('%.*f' % (decimals_exc, exc_final.tools[drill['tool']]['C']))
                    if exc_tool_dia == ordered_dia:
                        temp_drills.append(
                            {
                                "point": drill["point"],
                                "tool": str(current_tool)
                            }
                        )

                for slot in exc_final.slots:
                    slot_tool_dia = float('%.*f' % (decimals_exc, exc_final.tools[slot['tool']]['C']))
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

        self.units = self.app.defaults['units'].upper()

        for row in range(self.ui.tools_table.rowCount()):
            try:
                # if connected, disconnect the signal from the slot on item_changed as it creates issues
                offset_spin_widget = self.ui.tools_table.cellWidget(row, 4)
                offset_spin_widget.valueChanged.disconnect()
            except (TypeError, AttributeError):
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

            exc_id_item = QtWidgets.QTableWidgetItem('%d' % int(tool_no))
            exc_id_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)

            dia_item = QtWidgets.QTableWidgetItem('%.*f' % (self.decimals, self.tools[tool_no]['C']))
            dia_item.setFlags(QtCore.Qt.ItemIsEnabled)

            drill_count_item = QtWidgets.QTableWidgetItem('%d' % drill_cnt)
            drill_count_item.setFlags(QtCore.Qt.ItemIsEnabled)

            # if the slot number is zero is better to not clutter the GUI with zero's so we print a space
            slot_count_str = '%d' % slot_cnt if slot_cnt > 0 else ''
            slot_count_item = QtWidgets.QTableWidgetItem(slot_count_str)
            slot_count_item.setFlags(QtCore.Qt.ItemIsEnabled)

            try:
                t_offset = self.tool_offset[float('%.*f' % (self.decimals, float(self.tools[tool_no]['C'])))]
            except KeyError:
                t_offset = self.app.defaults['excellon_offset']

            tool_offset_item = FCDoubleSpinner()
            tool_offset_item.set_precision(self.decimals)
            tool_offset_item.set_range(-9999.9999, 9999.9999)
            tool_offset_item.setWrapping(True)
            tool_offset_item.setSingleStep(0.1) if self.units == 'MM' else tool_offset_item.setSingleStep(0.01)
            tool_offset_item.set_value(t_offset)

            plot_item = FCCheckBox()
            plot_item.setLayoutDirection(QtCore.Qt.RightToLeft)
            if self.ui.plot_cb.isChecked():
                plot_item.setChecked(True)

            self.ui.tools_table.setItem(self.tool_row, 0, exc_id_item)  # Tool name/id
            self.ui.tools_table.setItem(self.tool_row, 1, dia_item)  # Diameter
            self.ui.tools_table.setItem(self.tool_row, 2, drill_count_item)  # Number of drills per tool
            self.ui.tools_table.setItem(self.tool_row, 3, slot_count_item)  # Number of drills per tool
            self.ui.tools_table.setCellWidget(self.tool_row, 4, tool_offset_item)  # Tool offset
            empty_plot_item = QtWidgets.QTableWidgetItem('')
            empty_plot_item.setFlags(~QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.ui.tools_table.setItem(self.tool_row, 5, empty_plot_item)
            self.ui.tools_table.setCellWidget(self.tool_row, 5, plot_item)

            self.tool_row += 1

        # add a last row with the Total number of drills
        empty_1 = QtWidgets.QTableWidgetItem('')
        empty_1.setFlags(~QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        empty_1_1 = QtWidgets.QTableWidgetItem('')
        empty_1_1.setFlags(~QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        empty_1_2 = QtWidgets.QTableWidgetItem('')
        empty_1_2.setFlags(~QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        empty_1_3 = QtWidgets.QTableWidgetItem('')
        empty_1_3.setFlags(~QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)

        label_tot_drill_count = QtWidgets.QTableWidgetItem(_('Total Drills'))
        tot_drill_count = QtWidgets.QTableWidgetItem('%d' % self.tot_drill_cnt)
        label_tot_drill_count.setFlags(QtCore.Qt.ItemIsEnabled)
        tot_drill_count.setFlags(QtCore.Qt.ItemIsEnabled)

        self.ui.tools_table.setItem(self.tool_row, 0, empty_1)
        self.ui.tools_table.setItem(self.tool_row, 1, label_tot_drill_count)
        self.ui.tools_table.setItem(self.tool_row, 2, tot_drill_count)  # Total number of drills
        self.ui.tools_table.setItem(self.tool_row, 3, empty_1_1)
        self.ui.tools_table.setItem(self.tool_row, 4, empty_1_2)
        self.ui.tools_table.setItem(self.tool_row, 5, empty_1_3)

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
        empty_2_1 = QtWidgets.QTableWidgetItem('')
        empty_2_1.setFlags(~QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        empty_2_2 = QtWidgets.QTableWidgetItem('')
        empty_2_2.setFlags(~QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        empty_2_3 = QtWidgets.QTableWidgetItem('')
        empty_2_3.setFlags(~QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)

        label_tot_slot_count = QtWidgets.QTableWidgetItem(_('Total Slots'))
        tot_slot_count = QtWidgets.QTableWidgetItem('%d' % self.tot_slot_cnt)
        label_tot_slot_count.setFlags(QtCore.Qt.ItemIsEnabled)
        tot_slot_count.setFlags(QtCore.Qt.ItemIsEnabled)

        self.ui.tools_table.setItem(self.tool_row, 0, empty_2)
        self.ui.tools_table.setItem(self.tool_row, 1, label_tot_slot_count)
        self.ui.tools_table.setItem(self.tool_row, 2, empty_2_1)
        self.ui.tools_table.setItem(self.tool_row, 3, tot_slot_count)  # Total number of slots
        self.ui.tools_table.setItem(self.tool_row, 4, empty_2_2)
        self.ui.tools_table.setItem(self.tool_row, 5, empty_2_3)

        for kl in [1, 2, 3]:
            self.ui.tools_table.item(self.tool_row, kl).setFont(font)
            self.ui.tools_table.item(self.tool_row, kl).setForeground(QtGui.QColor(0, 70, 255))

        # sort the tool diameter column
        # self.ui.tools_table.sortItems(1)

        # all the tools are selected by default
        self.ui.tools_table.selectColumn(0)

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
        if self.app.defaults["global_app_level"] == 'b':
            horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        else:
            horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(4, QtWidgets.QHeaderView.Stretch)
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
            self.ui.tooldia_entry.hide()
            self.ui.generate_milling_button.hide()
        else:
            self.ui.tooldia_entry.show()
            self.ui.generate_milling_button.show()

        if not self.slots:
            self.ui.slot_tooldia_entry.hide()
            self.ui.generate_milling_slots_button.hide()
        else:
            self.ui.slot_tooldia_entry.show()
            self.ui.generate_milling_slots_button.show()

        # we reactivate the signals after the after the tool adding as we don't need to see the tool been populated
        for row in range(self.ui.tools_table.rowCount()):
            try:
                offset_spin_widget = self.ui.tools_table.cellWidget(row, 4)
                offset_spin_widget.valueChanged.connect(self.on_tool_offset_edit)
            except (TypeError, AttributeError):
                pass

        # set the text on tool_data_label after loading the object
        sel_rows = list()
        sel_items = self.ui.tools_table.selectedItems()
        for it in sel_items:
            sel_rows.append(it.row())
        if len(sel_rows) > 1:
            self.ui.tool_data_label.setText(
                "<b>%s: <font color='#0000FF'>%s</font></b>" % (_('Parameters for'), _("Multiple Tools"))
            )

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

        self.units = self.app.defaults['units'].upper()

        self.form_fields.update({
            "plot": self.ui.plot_cb,
            "solid": self.ui.solid_cb,
            "drillz": self.ui.cutz_entry,
            "travelz": self.ui.travelz_entry,
            "feedrate": self.ui.feedrate_z_entry,
            "feedrate_rapid": self.ui.feedrate_rapid_entry,
            "tooldia": self.ui.tooldia_entry,
            "slot_tooldia": self.ui.slot_tooldia_entry,
            "toolchange": self.ui.toolchange_cb,
            "toolchangez": self.ui.toolchangez_entry,
            "spindlespeed": self.ui.spindlespeed_entry,
            "dwell": self.ui.dwell_cb,
            "dwelltime": self.ui.dwelltime_entry,
            "startz": self.ui.estartz_entry,
            "endz": self.ui.endz_entry,
            "ppname_e": self.ui.pp_excellon_name_cb,
            "z_pdepth": self.ui.pdepth_entry,
            "feedrate_probe": self.ui.feedrate_probe_entry,
            "gcode_type": self.ui.excellon_gcode_type_radio
        })

        for name in list(self.app.preprocessors.keys()):
            # the HPGL preprocessor is only for Geometry not for Excellon job therefore don't add it
            if name == 'hpgl':
                continue
            self.ui.pp_excellon_name_cb.addItem(name)

        # Fill form fields
        self.to_form()

        # update the changes in UI depending on the selected preprocessor in Preferences
        # after this moment all the changes in the Posprocessor combo will be handled by the activated signal of the
        # self.ui.pp_excellon_name_cb combobox
        self.on_pp_changed()

        # initialize the dict that holds the tools offset
        t_default_offset = self.app.defaults["excellon_offset"]
        if not self.tool_offset:
            for value in self.tools.values():
                dia = float('%.*f' % (self.decimals, float(value['C'])))
                self.tool_offset[dia] = t_default_offset

        # Show/Hide Advanced Options
        if self.app.defaults["global_app_level"] == 'b':
            self.ui.level.setText('<span style="color:green;"><b>%s</b></span>' % _('Basic'))

            self.ui.tools_table.setColumnHidden(4, True)
            self.ui.tools_table.setColumnHidden(5, True)
            self.ui.estartz_label.hide()
            self.ui.estartz_entry.hide()
            self.ui.feedrate_rapid_label.hide()
            self.ui.feedrate_rapid_entry.hide()
            self.ui.pdepth_label.hide()
            self.ui.pdepth_entry.hide()
            self.ui.feedrate_probe_label.hide()
            self.ui.feedrate_probe_entry.hide()
        else:
            self.ui.level.setText('<span style="color:red;"><b>%s</b></span>' % _('Advanced'))

        assert isinstance(self.ui, ExcellonObjectUI), \
            "Expected a ExcellonObjectUI, got %s" % type(self.ui)
        self.ui.plot_cb.stateChanged.connect(self.on_plot_cb_click)
        self.ui.solid_cb.stateChanged.connect(self.on_solid_cb_click)
        self.ui.generate_cnc_button.clicked.connect(self.on_create_cncjob_button_click)
        self.ui.generate_milling_button.clicked.connect(self.on_generate_milling_button_click)
        self.ui.generate_milling_slots_button.clicked.connect(self.on_generate_milling_slots_button_click)

        self.on_operation_type(val='drill')
        self.ui.operation_radio.activated_custom.connect(self.on_operation_type)

        self.ui.pp_excellon_name_cb.activated.connect(self.on_pp_changed)
        self.units_found = self.app.defaults['units']

    def ui_connect(self):

        # selective plotting
        for row in range(self.ui.tools_table.rowCount() - 2):
            self.ui.tools_table.cellWidget(row, 5).clicked.connect(self.on_plot_cb_click_table)
        self.ui.plot_cb.stateChanged.connect(self.on_plot_cb_click)

        # rows selected
        self.ui.tools_table.clicked.connect(self.on_row_selection_change)
        self.ui.tools_table.horizontalHeader().sectionClicked.connect(self.on_row_selection_change)

    def ui_disconnect(self):
        # selective plotting
        for row in range(self.ui.tools_table.rowCount()):
            try:
                self.ui.tools_table.cellWidget(row, 5).clicked.disconnect()
            except (TypeError, AttributeError):
                pass
        try:
            self.ui.plot_cb.stateChanged.disconnect()
        except (TypeError, AttributeError):
            pass

        # rows selected
        try:
            self.ui.tools_table.clicked.disconnect()
        except (TypeError, AttributeError):
            pass
        try:
            self.ui.tools_table.horizontalHeader().sectionClicked.disconnect()
        except (TypeError, AttributeError):
            pass

    def on_row_selection_change(self):
        self.update_ui()

    def update_ui(self, row=None):
        self.ui_disconnect()

        if row is None:
            sel_rows = list()
            sel_items = self.ui.tools_table.selectedItems()
            for it in sel_items:
                sel_rows.append(it.row())
        else:
            sel_rows = row if type(row) == list else [row]

        if not sel_rows:
            self.ui.tool_data_label.setText(
                "<b>%s: <font color='#0000FF'>%s</font></b>" % (_('Parameters for'), _("No Tool Selected"))
            )
            self.ui.generate_cnc_button.setDisabled(True)
            self.ui.generate_milling_button.setDisabled(True)
            self.ui.generate_milling_slots_button.setDisabled(True)
            self.ui_connect()
            return
        else:
            self.ui.generate_cnc_button.setDisabled(False)
            self.ui.generate_milling_button.setDisabled(False)
            self.ui.generate_milling_slots_button.setDisabled(False)

        if len(sel_rows) == 1:
            # update the QLabel that shows for which Tool we have the parameters in the UI form
            tooluid = int(self.ui.tools_table.item(sel_rows[0], 0).text())
            self.ui.tool_data_label.setText(
                "<b>%s: <font color='#0000FF'>%s %d</font></b>" % (_('Parameters for'), _("Tool"), tooluid)
            )
        else:
            self.ui.tool_data_label.setText(
                "<b>%s: <font color='#0000FF'>%s</font></b>" % (_('Parameters for'), _("Multiple Tools"))
            )

        for c_row in sel_rows:
            # populate the form with the data from the tool associated with the row parameter
            try:
                item = self.ui.tools_table.item(c_row, 0)
                if type(item) is not None:
                    tooluid = int(item.text())
                else:
                    self.ui_connect()
                    return
            except Exception as e:
                log.debug("Tool missing. Add a tool in Geo Tool Table. %s" % str(e))
                self.ui_connect()
                return

            # try:
            #     # set the form with data from the newly selected tool
            #     for tooluid_key, tooluid_value in list(self.tools.items()):
            #         if int(tooluid_key) == tooluid:
            #             for key, value in tooluid_value.items():
            #                 if key == 'data':
            #                     form_value_storage = tooluid_value[key]
            #                     self.update_form(form_value_storage)
            # except Exception as e:
            #     log.debug("FlatCAMObj ---> update_ui() " + str(e))

        self.ui_connect()

    def on_operation_type(self, val):
        if val == 'mill':
            self.ui.mill_type_label.show()
            self.ui.mill_type_radio.show()
            self.ui.mill_dia_label.show()
            self.ui.mill_dia_entry.show()
            self.ui.frxylabel.show()
            self.ui.xyfeedrate_entry.show()
            self.ui.extracut_cb.show()
            self.ui.e_cut_entry.show()

            if 'laser' not in self.ui.pp_excellon_name_cb.get_value().lower():
                self.ui.mpass_cb.show()
                self.ui.maxdepth_entry.show()
        else:
            self.ui.mill_type_label.hide()
            self.ui.mill_type_radio.hide()
            self.ui.mill_dia_label.hide()
            self.ui.mill_dia_entry.hide()
            self.ui.mpass_cb.hide()
            self.ui.maxdepth_entry.hide()
            self.ui.frxylabel.hide()
            self.ui.xyfeedrate_entry.hide()
            self.ui.extracut_cb.hide()
            self.ui.e_cut_entry.hide()

    def on_tool_offset_edit(self):
        # if connected, disconnect the signal from the slot on item_changed as it creates issues
        for row in range(self.ui.tools_table.rowCount()):
            try:
                # if connected, disconnect the signal from the slot on item_changed as it creates issues
                offset_spin_widget = self.ui.tools_table.cellWidget(row, 4)
                offset_spin_widget.valueChanged.disconnect()
            except (TypeError, AttributeError):
                pass

        self.units = self.app.defaults['units'].upper()
        self.is_modified = True

        row_of_item_changed = self.ui.tools_table.currentRow()
        dia = float('%.*f' % (self.decimals, float(self.ui.tools_table.item(row_of_item_changed, 1).text())))

        self.tool_offset[dia] = self.sender().get_value()

        # we reactivate the signals after the after the tool editing
        for row in range(self.ui.tools_table.rowCount()):
            try:
                offset_spin_widget = self.ui.tools_table.cellWidget(row, 4)
                offset_spin_widget.valueChanged.connect(self.on_tool_offset_edit)
            except (TypeError, AttributeError):
                pass

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
            txt = ''
            elem = list()

            for column in range(0, self.ui.tools_table.columnCount() - 1):
                try:
                    txt = self.ui.tools_table.item(x.row(), column).text()
                except AttributeError:
                    try:
                        txt = self.ui.tools_table.cellWidget(x.row(), column).currentText()
                    except AttributeError:
                        pass
                elem.append(txt)
            table_tools_items.append(deepcopy(elem))
            # table_tools_items.append([self.ui.tools_table.item(x.row(), column).text()
            #                           for column in range(0, self.ui.tools_table.columnCount() - 1)])
        for item in table_tools_items:
            item[0] = str(item[0])
        return table_tools_items

    def export_excellon(self, whole, fract, e_zeros=None, form='dec', factor=1, slot_type='routing'):
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
                    excellon_code += 'G05\n'

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
                            if slot_type == 'routing':
                                excellon_code += "G00X{:.{dec}f}Y{:.{dec}f}\nM15\n".format(start_slot_x,
                                                                                           start_slot_y,
                                                                                           dec=fract)
                                excellon_code += "G01X{:.{dec}f}Y{:.{dec}f}\nM16\n".format(stop_slot_x,
                                                                                           stop_slot_y,
                                                                                           dec=fract)
                            elif slot_type == 'drilling':
                                excellon_code += "X{:.{dec}f}Y{:.{dec}f}G85X{:.{dec}f}Y{:.{dec}f}\nG05\n".format(
                                    start_slot_x, start_slot_y, stop_slot_x, stop_slot_y, dec=fract
                                )

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

                            if slot_type == 'routing':
                                excellon_code += "G00X{xstart}Y{ystart}\nM15\n".format(xstart=start_slot_x_formatted,
                                                                                       ystart=start_slot_y_formatted)
                                excellon_code += "G01X{xstop}Y{ystop}\nM16\n".format(xstop=stop_slot_x_formatted,
                                                                                     ystop=stop_slot_y_formatted)
                            elif slot_type == 'drilling':
                                excellon_code += "{xstart}Y{ystart}G85X{xstop}Y{ystop}\nG05\n".format(
                                    xstart=start_slot_x_formatted, ystart=start_slot_y_formatted,
                                    xstop=stop_slot_x_formatted, ystop=stop_slot_y_formatted
                                )
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

                            if slot_type == 'routing':
                                excellon_code += "G00X{xstart}Y{ystart}\nM15\n".format(xstart=start_slot_x_formatted,
                                                                                       ystart=start_slot_y_formatted)
                                excellon_code += "G01X{xstop}Y{ystop}\nM16\n".format(xstop=stop_slot_x_formatted,
                                                                                     ystop=stop_slot_y_formatted)
                            elif slot_type == 'drilling':
                                excellon_code += "{xstart}Y{ystart}G85X{xstop}Y{ystop}\nG05\n".format(
                                    xstart=start_slot_x_formatted, ystart=start_slot_y_formatted,
                                    xstop=stop_slot_x_formatted, ystop=stop_slot_y_formatted
                                )
        except Exception as e:
            log.debug(str(e))

        if not self.drills and not self.slots:
            log.debug("FlatCAMObj.FlatCAMExcellon.export_excellon() --> Excellon Object is empty: no drills, no slots.")
            return 'fail'

        return has_slots, excellon_code

    def generate_milling_drills(self, tools=None, outname=None, tooldia=None, plot=False, use_thread=False):
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
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("Please select one or more tools from the list and try again."))
            return False, "Error: No tools."

        for tool in tools:
            if tooldia > self.tools[tool]["C"]:
                self.app.inform.emit(
                    '[ERROR_NOTCL] %s %s: %s' % (
                        _("Milling tool for DRILLS is larger than hole size. Cancelled."),
                        _("Tool"),
                        str(tool)
                    )
                )
                return False, "Error: Milling tool is larger than hole."

        def geo_init(geo_obj, app_obj):
            assert isinstance(geo_obj, FlatCAMGeometry), \
                "Initializer expected a FlatCAMGeometry, got %s" % type(geo_obj)

            # ## Add properties to the object

            # get the tool_table items in a list of row items
            tool_table_items = self.get_selected_tools_table_items()
            # insert an information only element in the front
            tool_table_items.insert(0, [_("Tool_nr"), _("Diameter"), _("Drills_Nr"), _("Slots_Nr")])

            geo_obj.options['Tools_in_use'] = tool_table_items
            geo_obj.options['type'] = 'Excellon Geometry'
            geo_obj.options["cnctooldia"] = str(tooldia)

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
                app_obj.new_object("geometry", outname, geo_init, plot=plot)

            # Create a promise with the new name
            self.app.collection.promise(outname)

            # Send to worker
            self.app.worker_task.emit({'fcn': geo_thread, 'params': [self.app]})
        else:
            self.app.new_object("geometry", outname, geo_init, plot=plot)

        return True, ""

    def generate_milling_slots(self, tools=None, outname=None, tooldia=None, plot=True, use_thread=False):
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
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("Please select one or more tools from the list and try again."))
            return False, "Error: No tools."

        for tool in tools:
            # I add the 0.0001 value to account for the rounding error in converting from IN to MM and reverse
            adj_toolstable_tooldia = float('%.*f' % (self.decimals, float(tooldia)))
            adj_file_tooldia = float('%.*f' % (self.decimals, float(self.tools[tool]["C"])))
            if adj_toolstable_tooldia > adj_file_tooldia + 0.0001:
                self.app.inform.emit('[ERROR_NOTCL] %s' %
                                     _("Milling tool for SLOTS is larger than hole size. Cancelled."))
                return False, "Error: Milling tool is larger than hole."

        def geo_init(geo_obj, app_obj):
            assert isinstance(geo_obj, FlatCAMGeometry), \
                "Initializer expected a FlatCAMGeometry, got %s" % type(geo_obj)

            # ## Add properties to the object

            # get the tool_table items in a list of row items
            tool_table_items = self.get_selected_tools_table_items()
            # insert an information only element in the front
            tool_table_items.insert(0, [_("Tool_nr"), _("Diameter"), _("Drills_Nr"), _("Slots_Nr")])

            geo_obj.options['Tools_in_use'] = tool_table_items
            geo_obj.options['type'] = 'Excellon Geometry'
            geo_obj.options["cnctooldia"] = str(tooldia)

            geo_obj.solid_geometry = []

            # in case that the tool used has the same diameter with the hole, and since the maximum resolution
            # for FlatCAM is 6 decimals,
            # we add a tenth of the minimum value, meaning 0.0000001, which from our point of view is "almost zero"
            for slot in self.slots:
                if slot['tool'] in tools:
                    toolstable_tool = float('%.*f' % (self.decimals, float(tooldia)))
                    file_tool = float('%.*f' % (self.decimals, float(self.tools[tool]["C"])))

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
                app_obj.new_object("geometry", outname + '_slot', geo_init, plot=plot)

            # Create a promise with the new name
            self.app.collection.promise(outname)

            # Send to worker
            self.app.worker_task.emit({'fcn': geo_thread, 'params': [self.app]})
        else:
            self.app.new_object("geometry", outname + '_slot', geo_init, plot=plot)

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

        if 'marlin' in current_pp.lower() or 'custom' in current_pp.lower():
            self.ui.feedrate_rapid_label.show()
            self.ui.feedrate_rapid_entry.show()
        else:
            self.ui.feedrate_rapid_label.hide()
            self.ui.feedrate_rapid_entry.hide()

        if 'laser' in current_pp.lower():
            self.ui.cutzlabel.hide()
            self.ui.cutz_entry.hide()
            try:
                self.ui.mpass_cb.hide()
                self.ui.maxdepth_entry.hide()
            except AttributeError:
                pass

            if 'marlin' in current_pp.lower():
                self.ui.travelzlabel.setText('%s:' % _("Focus Z"))
                self.ui.endz_label.show()
                self.ui.endz_entry.show()
            else:
                self.ui.travelzlabel.hide()
                self.ui.travelz_entry.hide()

                self.ui.endz_label.hide()
                self.ui.endz_entry.hide()

            try:
                self.ui.frzlabel.hide()
                self.ui.feedrate_z_entry.hide()
            except AttributeError:
                pass

            self.ui.dwell_cb.hide()
            self.ui.dwelltime_entry.hide()

            self.ui.spindle_label.setText('%s:' % _("Laser Power"))

            try:
                self.ui.tool_offset_label.hide()
                self.ui.offset_entry.hide()
            except AttributeError:
                pass
        else:
            self.ui.cutzlabel.show()
            self.ui.cutz_entry.show()
            try:
                self.ui.mpass_cb.show()
                self.ui.maxdepth_entry.show()
            except AttributeError:
                pass

            self.ui.travelzlabel.setText('%s:' % _('Travel Z'))

            self.ui.travelzlabel.show()
            self.ui.travelz_entry.show()

            self.ui.endz_label.show()
            self.ui.endz_entry.show()

            try:
                self.ui.frzlabel.show()
                self.ui.feedrate_z_entry.show()
            except AttributeError:
                pass
            self.ui.dwell_cb.show()
            self.ui.dwelltime_entry.show()

            self.ui.spindle_label.setText('%s:' % _('Spindle speed'))

            try:
                self.ui.tool_offset_lbl.show()
                self.ui.offset_entry.show()
            except AttributeError:
                pass

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
                self.app.inform.emit('[ERROR_NOTCL] %s' %
                                     _("Please select one or more tools from the list and try again."))
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

            # ## Add properties to the object

            job_obj.origin_kind = 'excellon'

            job_obj.options['Tools_in_use'] = tool_table_items
            job_obj.options['type'] = 'Excellon'
            job_obj.options['ppname_e'] = pp_excellon_name

            job_obj.z_cut = float(self.options["drillz"])
            job_obj.tool_offset = self.tool_offset
            job_obj.z_move = float(self.options["travelz"])
            job_obj.feedrate = float(self.options["feedrate"])
            job_obj.feedrate_rapid = float(self.options["feedrate_rapid"])

            job_obj.spindlespeed = float(self.options["spindlespeed"]) if self.options["spindlespeed"] != 0 else None
            job_obj.spindledir = self.app.defaults['excellon_spindledir']
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

            job_obj.z_pdepth = float(self.options["z_pdepth"])
            job_obj.feedrate_probe = float(self.options["feedrate_probe"])

            # There could be more than one drill size...
            # job_obj.tooldia =   # TODO: duplicate variable!
            # job_obj.options["tooldia"] =

            tools_csv = ','.join(tools)
            ret_val = job_obj.generate_from_excellon_by_tool(
                self, tools_csv,
                drillz=float(self.options['drillz']),
                toolchange=self.options["toolchange"],
                toolchangexy=self.app.defaults["excellon_toolchangexy"],
                toolchangez=float(self.options["toolchangez"]),
                startz=float(self.options["startz"]) if self.options["startz"] else None,
                endz=float(self.options["endz"]),
                excellon_optimization_type=self.app.defaults["excellon_optimization_type"])

            if ret_val == 'fail':
                return 'fail'

            job_obj.gcode_parse()
            job_obj.create_geometry()

        # To be run in separate thread
        def job_thread(app_obj):
            with self.app.proc_container.new(_("Generating CNC Code")):
                app_obj.new_object("cncjob", job_name, job_init)

        # Create promise for the new name.
        self.app.collection.promise(job_name)

        # Send to worker
        # self.app.worker.add_task(job_thread, [self.app])
        self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})

    def convert_units(self, units):
        log.debug("FlatCAMObj.FlatCAMExcellon.convert_units()")

        Excellon.convert_units(self, units)

        # factor = Excellon.convert_units(self, units)
        # self.options['drillz'] = float(self.options['drillz']) * factor
        # self.options['travelz'] = float(self.options['travelz']) * factor
        # self.options['feedrate'] = float(self.options['feedrate']) * factor
        # self.options['feedrate_rapid'] = float(self.options['feedrate_rapid']) * factor
        # self.options['toolchangez'] = float(self.options['toolchangez']) * factor
        #
        # if self.app.defaults["excellon_toolchangexy"] == '':
        #     self.options['toolchangexy'] = "0.0, 0.0"
        # else:
        #     coords_xy = [float(eval(coord)) for coord in self.app.defaults["excellon_toolchangexy"].split(",")]
        #     if len(coords_xy) < 2:
        #         self.app.inform.emit('[ERROR] %s' % _("The Toolchange X,Y field in Edit -> Preferences has to be "
        #                                               "in the format (x, y) \n"
        #                                               "but now there is only one value, not two. "))
        #         return 'fail'
        #     coords_xy[0] *= factor
        #     coords_xy[1] *= factor
        #     self.options['toolchangexy'] = "%f, %f" % (coords_xy[0], coords_xy[1])
        #
        # if self.options['startz'] is not None:
        #     self.options['startz'] = float(self.options['startz']) * factor
        # self.options['endz'] = float(self.options['endz']) * factor

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

    def plot(self, visible=None, kind=None):

        # Does all the required setup and returns False
        # if the 'ptint' option is set to False.
        if not FlatCAMObj.plot(self):
            return

        # try:
        #     # Plot Excellon (All polygons?)
        #     if self.options["solid"]:
        #         for tool in self.tools:
        #             for geo in self.tools[tool]['solid_geometry']:
        #                 self.add_shape(shape=geo, color='#750000BF', face_color='#C40000BF',
        #                                visible=self.options['plot'],
        #                                layer=2)
        #     else:
        #         for tool in self.tools:
        #             for geo in self.tools[tool]['solid_geometry']:
        #                 self.add_shape(shape=geo.exterior, color='red', visible=self.options['plot'])
        #                 for ints in geo.interiors:
        #                     self.add_shape(shape=ints, color='orange', visible=self.options['plot'])
        #
        #     self.shapes.redraw()
        #     return
        # except (ObjectDeleted, AttributeError, KeyError):
        #     self.shapes.clear(update=True)

        # this stays for compatibility reasons, in case we try to open old projects
        try:
            __ = iter(self.solid_geometry)
        except TypeError:
            self.solid_geometry = [self.solid_geometry]

        visible = visible if visible else self.options['plot']

        try:
            # Plot Excellon (All polygons?)
            if self.options["solid"]:
                for geo in self.solid_geometry:
                    self.add_shape(shape=geo,
                                   color=self.outline_color,
                                   face_color=self.fill_color,
                                   visible=visible,
                                   layer=2)
            else:
                for geo in self.solid_geometry:
                    self.add_shape(shape=geo.exterior, color='red', visible=visible)
                    for ints in geo.interiors:
                        self.add_shape(shape=ints, color='orange', visible=visible)

            self.shapes.redraw()
        except (ObjectDeleted, AttributeError):
            self.shapes.clear(update=True)


class FlatCAMGeometry(FlatCAMObj, Geometry):
    """
    Geometric object not associated with a specific
    format.
    """
    optionChanged = QtCore.pyqtSignal(str)
    ui_type = GeometryObjectUI

    def __init__(self, name):
        self.decimals = self.app.decimals

        self.circle_steps = int(self.app.defaults["geometry_circle_steps"])

        FlatCAMObj.__init__(self, name)
        Geometry.__init__(self, geo_steps_per_circle=self.circle_steps)

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
            "spindlespeed": 0,
            "dwell": True,
            "dwelltime": 1000,
            "multidepth": False,
            "depthperpass": 0.002,
            "extracut": False,
            "extracut_length": 0.1,
            "endz": 2.0,
            "startz": None,
            "toolchange": False,
            "toolchangez": 1.0,
            "toolchangexy": "0.0, 0.0",
            "ppname_g": 'default',
            "z_pdepth": -0.02,
            "feedrate_probe": 3.0,
        })

        if "cnctooldia" not in self.options:
            if type(self.app.defaults["geometry_cnctooldia"]) == float:
                self.options["cnctooldia"] = self.app.defaults["geometry_cnctooldia"]
            else:
                try:
                    tools_string = self.app.defaults["geometry_cnctooldia"].split(",")
                    tools_diameters = [eval(a) for a in tools_string if a != '']
                    self.options["cnctooldia"] = tools_diameters[0] if tools_diameters else 0.0
                except Exception as e:
                    log.debug("FlatCAMObj.FlatCAMGeometry.init() --> %s" % str(e))

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

        self.offset_item_options = ["Path", "In", "Out", "Custom"]
        self.type_item_options = [_("Iso"), _("Rough"), _("Finish")]
        self.tool_type_item_options = ["C1", "C2", "C3", "C4", "B", "V"]

        # flag to store if the V-Shape tool is selected in self.ui.geo_tools_table
        self.v_tool_type = None

        # flag to store if the Geometry is type 'multi-geometry' meaning that each tool has it's own geometry
        # the default value is False
        self.multigeo = False

        # flag to store if the geometry is part of a special group of geometries that can't be processed by the default
        # engine of FlatCAM. Most likely are generated by some of tools and are special cases of geometries.
        self.special_group = None

        self.old_pp_state = self.app.defaults["geometry_multidepth"]
        self.old_toolchangeg_state = self.app.defaults["geometry_toolchange"]
        self.units_found = self.app.defaults['units']

        # this variable can be updated by the Object that generates the geometry
        self.tool_type = 'C1'

        # save here the old value for the Cut Z before it is changed by selecting a V-shape type tool in the tool table
        self.old_cutz = self.app.defaults["geometry_cutz"]

        self.fill_color = self.app.defaults['geometry_plot_line']
        self.outline_color = self.app.defaults['geometry_plot_line']
        self.alpha_level = 'FF'

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from predecessors.
        self.ser_attrs += ['options', 'kind', 'tools', 'multigeo']

    def build_ui(self):
        self.ui_disconnect()
        FlatCAMObj.build_ui(self)

        self.units = self.app.defaults['units']

        offset = 0
        tool_idx = 0

        n = len(self.tools)
        self.ui.geo_tools_table.setRowCount(n)

        for tooluid_key, tooluid_value in self.tools.items():
            tool_idx += 1
            row_no = tool_idx - 1

            tool_id = QtWidgets.QTableWidgetItem('%d' % int(tool_idx))
            tool_id.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.ui.geo_tools_table.setItem(row_no, 0, tool_id)  # Tool name/id

            # Make sure that the tool diameter when in MM is with no more than 2 decimals.
            # There are no tool bits in MM with more than 3 decimals diameter.
            # For INCH the decimals should be no more than 3. There are no tools under 10mils.

            dia_item = QtWidgets.QTableWidgetItem('%.*f' % (self.decimals, float(tooluid_value['tooldia'])))

            dia_item.setFlags(QtCore.Qt.ItemIsEnabled)

            offset_item = QtWidgets.QComboBox()
            for item in self.offset_item_options:
                offset_item.addItem(item)
            # offset_item.setStyleSheet('background-color: rgb(255,255,255)')
            idx = offset_item.findText(tooluid_value['offset'])
            offset_item.setCurrentIndex(idx)

            type_item = QtWidgets.QComboBox()
            for item in self.type_item_options:
                type_item.addItem(item)
            # type_item.setStyleSheet('background-color: rgb(255,255,255)')
            idx = type_item.findText(tooluid_value['type'])
            type_item.setCurrentIndex(idx)

            tool_type_item = QtWidgets.QComboBox()
            for item in self.tool_type_item_options:
                tool_type_item.addItem(item)
                # tool_type_item.setStyleSheet('background-color: rgb(255,255,255)')
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

            # ## REMEMBER: THIS COLUMN IS HIDDEN IN OBJECTUI.PY ###
            self.ui.geo_tools_table.setItem(row_no, 5, tool_uid_item)  # Tool unique ID
            self.ui.geo_tools_table.setCellWidget(row_no, 6, plot_item)

            try:
                self.ui.tool_offset_entry.set_value(tooluid_value['offset_value'])
            except Exception as e:
                log.debug("build_ui() --> Could not set the 'offset_value' key in self.tools. Error: %s" % str(e))

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

        # HACK: for whatever reasons the name in Selected tab is reverted to the original one after a successful rename
        # done in the collection view but only for Geometry objects. Perhaps some references remains. Should be fixed.
        self.ui.name_entry.set_value(self.options['name'])
        self.ui_connect()

        self.ui.e_cut_entry.setDisabled(False) if self.ui.extracut_cb.get_value() else \
            self.ui.e_cut_entry.setDisabled(True)

        # set the text on tool_data_label after loading the object
        sel_rows = list()
        sel_items = self.ui.geo_tools_table.selectedItems()
        for it in sel_items:
            sel_rows.append(it.row())
        if len(sel_rows) > 1:
            self.ui.tool_data_label.setText(
                "<b>%s: <font color='#0000FF'>%s</font></b>" % (_('Parameters for'), _("Multiple Tools"))
            )

    def set_ui(self, ui):
        FlatCAMObj.set_ui(self, ui)

        log.debug("FlatCAMGeometry.set_ui()")

        assert isinstance(self.ui, GeometryObjectUI), \
            "Expected a GeometryObjectUI, got %s" % type(self.ui)

        self.units = self.app.defaults['units'].upper()
        self.units_found = self.app.defaults['units']

        # populate preprocessor names in the combobox
        for name in list(self.app.preprocessors.keys()):
            self.ui.pp_geometry_name_cb.addItem(name)

        self.form_fields.update({
            "plot": self.ui.plot_cb,
            "cutz": self.ui.cutz_entry,
            "vtipdia": self.ui.tipdia_entry,
            "vtipangle": self.ui.tipangle_entry,
            "travelz": self.ui.travelz_entry,
            "feedrate": self.ui.cncfeedrate_entry,
            "feedrate_z": self.ui.feedrate_z_entry,
            "feedrate_rapid": self.ui.feedrate_rapid_entry,
            "spindlespeed": self.ui.cncspindlespeed_entry,
            "dwell": self.ui.dwell_cb,
            "dwelltime": self.ui.dwelltime_entry,
            "multidepth": self.ui.mpass_cb,
            "ppname_g": self.ui.pp_geometry_name_cb,
            "z_pdepth": self.ui.pdepth_entry,
            "feedrate_probe": self.ui.feedrate_probe_entry,
            "depthperpass": self.ui.maxdepth_entry,
            "extracut": self.ui.extracut_cb,
            "extracut_length": self.ui.e_cut_entry,
            "toolchange": self.ui.toolchangeg_cb,
            "toolchangez": self.ui.toolchangez_entry,
            "endz": self.ui.endz_entry,
            "cnctooldia": self.ui.addtool_entry
        })

        # Fill form fields only on object create
        self.to_form()

        # update the changes in UI depending on the selected preprocessor in Preferences
        # after this moment all the changes in the Posprocessor combo will be handled by the activated signal of the
        # self.ui.pp_geometry_name_cb combobox
        self.on_pp_changed()

        self.ui.tipdialabel.hide()
        self.ui.tipdia_entry.hide()
        self.ui.tipanglelabel.hide()
        self.ui.tipangle_entry.hide()
        self.ui.cutz_entry.setDisabled(False)

        # store here the default data for Geometry Data
        self.default_data = dict()
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
            "extracut_length": None,
            "toolchange": None,
            "toolchangez": None,
            "endz": None,
            "spindlespeed": 0,
            "toolchangexy": None,
            "startz": None
        })

        # fill in self.default_data values from self.options
        for def_key in self.default_data:
            for opt_key, opt_val in self.options.items():
                if def_key == opt_key:
                    self.default_data[def_key] = deepcopy(opt_val)

        if type(self.options["cnctooldia"]) == float:
            tools_list = [self.options["cnctooldia"]]
        else:
            try:
                temp_tools = self.options["cnctooldia"].split(",")
                tools_list = [
                    float(eval(dia)) for dia in temp_tools if dia != ''
                ]
            except Exception as e:
                log.error("FlatCAMGeometry.set_ui() -> At least one tool diameter needed. "
                          "Verify in Edit -> Preferences -> Geometry General -> Tool dia. %s" % str(e))
                return

        self.tooluid += 1

        if not self.tools:
            for toold in tools_list:
                new_data = deepcopy(self.default_data)
                self.tools.update({
                    self.tooluid: {
                        'tooldia': float('%.*f' % (self.decimals, float(toold))),
                        'offset': 'Path',
                        'offset_value': 0.0,
                        'type': _('Rough'),
                        'tool_type': self.tool_type,
                        'data': new_data,
                        'solid_geometry': self.solid_geometry
                    }
                })
                self.tooluid += 1
        else:
            # if self.tools is not empty then it can safely be assumed that it comes from an opened project.
            # Because of the serialization the self.tools list on project save, the dict keys (members of self.tools
            # are each a dict) are turned into strings so we rebuild the self.tools elements so the keys are
            # again float type; dict's don't like having keys changed when iterated through therefore the need for the
            # following convoluted way of changing the keys from string to float type
            temp_tools = {}
            for tooluid_key in self.tools:
                val = deepcopy(self.tools[tooluid_key])
                new_key = deepcopy(int(tooluid_key))
                temp_tools[new_key] = val

            self.tools.clear()
            self.tools = deepcopy(temp_tools)

        self.ui.tool_offset_entry.hide()
        self.ui.tool_offset_lbl.hide()

        # used to store the state of the mpass_cb if the selected preprocessor for geometry is hpgl
        self.old_pp_state = self.default_data['multidepth']
        self.old_toolchangeg_state = self.default_data['toolchange']

        if not isinstance(self.ui, GeometryObjectUI):
            log.debug("Expected a GeometryObjectUI, got %s" % type(self.ui))
            return

        self.ui.geo_tools_table.setupContextMenu()
        self.ui.geo_tools_table.addContextMenu(
            _("Add from Tool DB"), self.on_tool_add_from_db_clicked,
            icon=QtGui.QIcon(self.app.resource_location + "/plus16.png"))
        self.ui.geo_tools_table.addContextMenu(
            _("Copy"), self.on_tool_copy,
            icon=QtGui.QIcon(self.app.resource_location + "/copy16.png"))
        self.ui.geo_tools_table.addContextMenu(
            _("Delete"), lambda: self.on_tool_delete(all=None),
            icon=QtGui.QIcon(self.app.resource_location + "/delete32.png"))

        # Show/Hide Advanced Options
        if self.app.defaults["global_app_level"] == 'b':
            self.ui.level.setText('<span style="color:green;"><b>%s</b></span>' % _('Basic'))

            self.ui.geo_tools_table.setColumnHidden(2, True)
            self.ui.geo_tools_table.setColumnHidden(3, True)
            # self.ui.geo_tools_table.setColumnHidden(4, True)
            self.ui.addtool_entry_lbl.hide()
            self.ui.addtool_entry.hide()
            self.ui.addtool_btn.hide()
            self.ui.copytool_btn.hide()
            self.ui.deltool_btn.hide()
            # self.ui.endz_label.hide()
            # self.ui.endz_entry.hide()
            self.ui.fr_rapidlabel.hide()
            self.ui.feedrate_rapid_entry.hide()
            self.ui.extracut_cb.hide()
            self.ui.e_cut_entry.hide()
            self.ui.pdepth_label.hide()
            self.ui.pdepth_entry.hide()
            self.ui.feedrate_probe_label.hide()
            self.ui.feedrate_probe_entry.hide()
        else:
            self.ui.level.setText('<span style="color:red;"><b>%s</b></span>' % _('Advanced'))

        self.ui.e_cut_entry.setDisabled(False) if self.app.defaults['geometry_extracut'] else \
            self.ui.e_cut_entry.setDisabled(True)
        self.ui.extracut_cb.toggled.connect(lambda state: self.ui.e_cut_entry.setDisabled(not state))

        self.ui.plot_cb.stateChanged.connect(self.on_plot_cb_click)
        self.ui.generate_cnc_button.clicked.connect(self.on_generatecnc_button_click)
        self.ui.paint_tool_button.clicked.connect(lambda: self.app.paint_tool.run(toggle=False))
        self.ui.generate_ncc_button.clicked.connect(lambda: self.app.ncclear_tool.run(toggle=False))
        self.ui.pp_geometry_name_cb.activated.connect(self.on_pp_changed)

        self.ui.tipdia_entry.valueChanged.connect(self.update_cutz)
        self.ui.tipangle_entry.valueChanged.connect(self.update_cutz)

        self.ui.addtool_from_db_btn.clicked.connect(self.on_tool_add_from_db_clicked)
        self.ui.apply_param_to_all.clicked.connect(self.on_apply_param_to_all_clicked)
        self.ui.cutz_entry.returnPressed.connect(self.on_cut_z_changed)

    def on_cut_z_changed(self):
        self.old_cutz = self.ui.cutz_entry.get_value()

    def set_tool_offset_visibility(self, current_row):
        if current_row is None:
            return
        try:
            tool_offset = self.ui.geo_tools_table.cellWidget(current_row, 2)
            if tool_offset is not None:
                tool_offset_txt = tool_offset.currentText()
                if tool_offset_txt == 'Custom':
                    self.ui.tool_offset_entry.show()
                    self.ui.tool_offset_lbl.show()
                else:
                    self.ui.tool_offset_entry.hide()
                    self.ui.tool_offset_lbl.hide()
        except Exception as e:
            log.debug("set_tool_offset_visibility() --> " + str(e))
            return

    def on_offset_value_edited(self):
        """
        This will save the offset_value into self.tools storage whenever the offset value is edited
        :return:
        """

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
                            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                                 _("Wrong value format entered, use a number."))
                            return

    def ui_connect(self):
        # on any change to the widgets that matter it will be called self.gui_form_to_storage which will save the
        # changes in geometry UI
        for i in range(self.ui.grid3.count()):
            current_widget = self.ui.grid3.itemAt(i).widget()
            if isinstance(current_widget, FCCheckBox):
                current_widget.stateChanged.connect(self.gui_form_to_storage)
            elif isinstance(current_widget, FCComboBox):
                current_widget.currentIndexChanged.connect(self.gui_form_to_storage)
            elif isinstance(current_widget, FloatEntry) or isinstance(current_widget, LengthEntry) or \
                    isinstance(current_widget, FCEntry) or isinstance(current_widget, IntEntry):
                current_widget.editingFinished.connect(self.gui_form_to_storage)
            elif isinstance(current_widget, FCSpinner) or isinstance(current_widget, FCDoubleSpinner):
                current_widget.returnPressed.connect(self.gui_form_to_storage)

        for row in range(self.ui.geo_tools_table.rowCount()):
            for col in [2, 3, 4]:
                self.ui.geo_tools_table.cellWidget(row, col).currentIndexChanged.connect(
                    self.on_tooltable_cellwidget_change)

        # I use lambda's because the connected functions have parameters that could be used in certain scenarios
        self.ui.addtool_btn.clicked.connect(lambda: self.on_tool_add())

        self.ui.copytool_btn.clicked.connect(lambda: self.on_tool_copy())
        self.ui.deltool_btn.clicked.connect(lambda: self.on_tool_delete())

        # self.ui.geo_tools_table.currentItemChanged.connect(self.on_row_selection_change)
        self.ui.geo_tools_table.clicked.connect(self.on_row_selection_change)
        self.ui.geo_tools_table.horizontalHeader().sectionClicked.connect(self.on_row_selection_change)

        self.ui.geo_tools_table.itemChanged.connect(self.on_tool_edit)
        self.ui.tool_offset_entry.returnPressed.connect(self.on_offset_value_edited)

        for row in range(self.ui.geo_tools_table.rowCount()):
            self.ui.geo_tools_table.cellWidget(row, 6).clicked.connect(self.on_plot_cb_click_table)
        self.ui.plot_cb.stateChanged.connect(self.on_plot_cb_click)

        # common parameters update
        self.ui.pp_geometry_name_cb.currentIndexChanged.connect(self.update_common_param_in_storage)

    def ui_disconnect(self):

        # on any change to the widgets that matter it will be called self.gui_form_to_storage which will save the
        # changes in geometry UI
        for i in range(self.ui.grid3.count()):
            current_widget = self.ui.grid3.itemAt(i).widget()
            if isinstance(current_widget, FCCheckBox):
                try:
                    self.ui.grid3.itemAt(i).widget().stateChanged.disconnect(self.gui_form_to_storage)
                except (TypeError, AttributeError):
                    pass
            elif isinstance(current_widget, FCComboBox):
                try:
                    self.ui.grid3.itemAt(i).widget().currentIndexChanged.disconnect(self.gui_form_to_storage)
                except (TypeError, AttributeError):
                    pass
            elif isinstance(current_widget, LengthEntry) or isinstance(current_widget, IntEntry) or \
                    isinstance(current_widget, FCEntry) or isinstance(current_widget, FloatEntry):
                try:
                    self.ui.grid3.itemAt(i).widget().editingFinished.disconnect(self.gui_form_to_storage)
                except (TypeError, AttributeError):
                    pass
            elif isinstance(current_widget, FCSpinner) or isinstance(current_widget, FCDoubleSpinner):
                try:
                    self.ui.grid3.itemAt(i).widget().returnPressed.disconnect(self.gui_form_to_storage)
                except TypeError:
                    pass

        for row in range(self.ui.geo_tools_table.rowCount()):
            for col in [2, 3, 4]:
                try:
                    self.ui.geo_tools_table.cellWidget(row, col).currentIndexChanged.disconnect()
                except (TypeError, AttributeError):
                    pass

        try:
            self.ui.addtool_btn.clicked.disconnect()
        except (TypeError, AttributeError):
            pass

        try:
            self.ui.copytool_btn.clicked.disconnect()
        except (TypeError, AttributeError):
            pass

        try:
            self.ui.deltool_btn.clicked.disconnect()
        except (TypeError, AttributeError):
            pass

        try:
            self.ui.geo_tools_table.clicked.disconnect()
        except (TypeError, AttributeError):
            pass
        try:
            self.ui.geo_tools_table.horizontalHeader().sectionClicked.disconnect()
        except (TypeError, AttributeError):
            pass

        try:
            self.ui.geo_tools_table.itemChanged.disconnect()
        except (TypeError, AttributeError):
            pass

        try:
            self.ui.tool_offset_entry.returnPressed.disconnect()
        except (TypeError, AttributeError):
            pass

        for row in range(self.ui.geo_tools_table.rowCount()):
            try:
                self.ui.geo_tools_table.cellWidget(row, 6).clicked.disconnect()
            except (TypeError, AttributeError):
                pass

        try:
            self.ui.plot_cb.stateChanged.disconnect()
        except (TypeError, AttributeError):
            pass

    def on_row_selection_change(self):
        self.update_ui()

    def update_ui(self, row=None):
        self.ui_disconnect()

        if row is None:
            sel_rows = list()
            sel_items = self.ui.geo_tools_table.selectedItems()
            for it in sel_items:
                sel_rows.append(it.row())
        else:
            sel_rows = row if type(row) == list else [row]

        if not sel_rows:
            sel_rows = [0]

        for current_row in sel_rows:
            self.set_tool_offset_visibility(current_row)

            # populate the form with the data from the tool associated with the row parameter
            try:
                item = self.ui.geo_tools_table.item(current_row, 5)
                if type(item) is not None:
                    tooluid = int(item.text())
                else:
                    self.ui_connect()
                    return
            except Exception as e:
                log.debug("Tool missing. Add a tool in Geo Tool Table. %s" % str(e))
                self.ui_connect()
                return

            # update the QLabel that shows for which Tool we have the parameters in the UI form
            if len(sel_rows) == 1:
                self.ui.tool_data_label.setText(
                    "<b>%s: <font color='#0000FF'>%s %d</font></b>" % (_('Parameters for'), _("Tool"), tooluid)
                )
            else:
                self.ui.tool_data_label.setText(
                    "<b>%s: <font color='#0000FF'>%s</font></b>" % (_('Parameters for'), _("Multiple Tools"))
                )

            # update the form with the V-Shape fields if V-Shape selected in the geo_tool_table
            # also modify the Cut Z form entry to reflect the calculated Cut Z from values got from V-Shape Fields
            try:
                item = self.ui.geo_tools_table.cellWidget(current_row, 4)
                if item is not None:
                    tool_type_txt = item.currentText()
                    self.ui_update_v_shape(tool_type_txt=tool_type_txt)
                else:
                    self.ui_connect()
                    return
            except Exception as e:
                log.debug("Tool missing in ui_update_v_shape(). Add a tool in Geo Tool Table. %s" % str(e))
                return

            try:
                # set the form with data from the newly selected tool
                for tooluid_key, tooluid_value in self.tools.items():
                    if int(tooluid_key) == tooluid:
                        for key, value in tooluid_value.items():
                            if key == 'data':
                                form_value_storage = tooluid_value['data']
                                self.update_form(form_value_storage)
                            if key == 'offset_value':
                                # update the offset value in the entry even if the entry is hidden
                                self.ui.tool_offset_entry.set_value(tooluid_value['offset_value'])

                            if key == 'tool_type' and value == 'V':
                                self.update_cutz()
            except Exception as e:
                log.debug("FlatCAMGeometry.update_ui() -> %s " % str(e))

        self.ui_connect()

    def on_tool_add(self, dia=None):
        self.ui_disconnect()

        self.units = self.app.defaults['units'].upper()

        if dia is not None:
            tooldia = dia
        else:
            tooldia = float(self.ui.addtool_entry.get_value())

        # construct a list of all 'tooluid' in the self.tools
        # tool_uid_list = list()
        # for tooluid_key in self.tools:
        #     tool_uid_list.append(int(tooluid_key))
        tool_uid_list = [int(tooluid_key) for tooluid_key in self.tools]

        # find maximum from the temp_uid, add 1 and this is the new 'tooluid'
        max_uid = max(tool_uid_list) if tool_uid_list else 0
        self.tooluid = max_uid + 1

        tooldia = float('%.*f' % (self.decimals, tooldia))

        # here we actually add the new tool; if there is no tool in the tool table we add a tool with default data
        # otherwise we add a tool with data copied from last tool
        if self.tools:
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
        else:
            self.tools.update({
                self.tooluid: {
                    'tooldia': tooldia,
                    'offset': 'Path',
                    'offset_value': 0.0,
                    'type': _('Rough'),
                    'tool_type': 'C1',
                    'data': deepcopy(self.default_data),
                    'solid_geometry': self.solid_geometry
                }
            })

        self.tools[self.tooluid]['data']['name'] = self.options['name']

        self.ui.tool_offset_entry.hide()
        self.ui.tool_offset_lbl.hide()

        # we do this HACK to make sure the tools attribute to be serialized is updated in the self.ser_attrs list
        try:
            self.ser_attrs.remove('tools')
        except TypeError:
            pass
        self.ser_attrs.append('tools')

        self.app.inform.emit('[success] %s' % _("Tool added in Tool Table."))
        self.ui_connect()
        self.build_ui()

        # if there is no tool left in the Tools Table, enable the parameters GUI
        if self.ui.geo_tools_table.rowCount() != 0:
            self.ui.geo_param_frame.setDisabled(False)

    def on_tool_add_from_db_clicked(self):
        """
        Called when the user wants to add a new tool from Tools Database. It will create the Tools Database object
        and display the Tools Database tab in the form needed for the Tool adding
        :return: None
        """

        # if the Tools Database is already opened focus on it
        for idx in range(self.app.ui.plot_tab_area.count()):
            if self.app.ui.plot_tab_area.tabText(idx) == _("Tools Database"):
                self.app.ui.plot_tab_area.setCurrentWidget(self.app.tools_db_tab)
                break
        self.app.on_tools_database()
        self.app.tools_db_tab.buttons_frame.hide()
        self.app.tools_db_tab.add_tool_from_db.show()
        self.app.tools_db_tab.cancel_tool_from_db.show()

    def on_tool_from_db_inserted(self, tool):
        """
        Called from the Tools DB object through a App method when adding a tool from Tools Database
        :param tool: a dict with the tool data
        :return: None
        """

        self.ui_disconnect()
        self.units = self.app.defaults['units'].upper()

        tooldia = float(tool['tooldia'])

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

        tooldia = float('%.*f' % (self.decimals, tooldia))

        self.tools.update({
            self.tooluid: {
                'tooldia': tooldia,
                'offset': tool['offset'],
                'offset_value': float(tool['offset_value']),
                'type': tool['type'],
                'tool_type': tool['tool_type'],
                'data': deepcopy(tool['data']),
                'solid_geometry': self.solid_geometry
            }
        })

        self.tools[self.tooluid]['data']['name'] = self.options['name']

        self.ui.tool_offset_entry.hide()
        self.ui.tool_offset_lbl.hide()

        # we do this HACK to make sure the tools attribute to be serialized is updated in the self.ser_attrs list
        try:
            self.ser_attrs.remove('tools')
        except TypeError:
            pass
        self.ser_attrs.append('tools')

        self.ui_connect()
        self.build_ui()

        # if there is no tool left in the Tools Table, enable the parameters GUI
        if self.ui.geo_tools_table.rowCount() != 0:
            self.ui.geo_param_frame.setDisabled(False)

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
                        self.app.inform.emit('[WARNING_NOTCL] %s' % _("Failed. Select a tool to copy."))
                        self.ui_connect()
                        self.build_ui()
                        return
                    except Exception as e:
                        log.debug("on_tool_copy() --> " + str(e))
                # deselect the table
                # self.ui.geo_tools_table.clearSelection()
            else:
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("Failed. Select a tool to copy."))
                self.ui_connect()
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
        except ValueError:
            pass
        self.ser_attrs.append('tools')

        self.ui_connect()
        self.build_ui()
        self.app.inform.emit('[success] %s' % _("Tool was copied in Tool Table."))

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
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("Wrong value format entered, use a number."))
                return

        tool_dia = float('%.*f' % (self.decimals, d))
        tooluid = int(self.ui.geo_tools_table.item(current_row, 5).text())

        self.tools[tooluid]['tooldia'] = tool_dia

        try:
            self.ser_attrs.remove('tools')
            self.ser_attrs.append('tools')
        except (TypeError, ValueError):
            pass

        self.app.inform.emit('[success] %s' % _("Tool was edited in Tool Table."))
        self.ui_connect()
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
                        self.app.inform.emit('[WARNING_NOTCL] %s' % _("Failed. Select a tool to delete."))
                        self.ui_connect()
                        self.build_ui()
                        return
                    except Exception as e:
                        log.debug("on_tool_delete() --> " + str(e))
                # deselect the table
                # self.ui.geo_tools_table.clearSelection()
            else:
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("Failed. Select a tool to delete."))
                self.ui_connect()
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
        except TypeError:
            pass
        self.ser_attrs.append('tools')

        self.ui_connect()
        self.build_ui()
        self.app.inform.emit('[success] %s' % _("Tool was deleted in Tool Table."))

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
            except Exception as e:
                obj_active.options['xmin'] = 0
                obj_active.options['ymin'] = 0
                obj_active.options['xmax'] = 0
                obj_active.options['ymax'] = 0

        # if there is no tool left in the Tools Table, disable the parameters GUI
        if self.ui.geo_tools_table.rowCount() == 0:
            self.ui.geo_param_frame.setDisabled(True)

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
        vdia = float(self.ui.tipdia_entry.get_value())
        half_vangle = float(self.ui.tipangle_entry.get_value()) / 2

        row = self.ui.geo_tools_table.currentRow()
        tool_uid_item = self.ui.geo_tools_table.item(row, 5)
        if tool_uid_item is None:
            return
        tool_uid = int(tool_uid_item.text())

        tool_dia_item = self.ui.geo_tools_table.item(row, 1)
        if tool_dia_item is None:
            return
        tooldia = float(tool_dia_item.text())

        try:
            new_cutz = (tooldia - vdia) / (2 * math.tan(math.radians(half_vangle)))
        except ZeroDivisionError:
            new_cutz = self.old_cutz

        new_cutz = float('%.*f' % (self.decimals, new_cutz)) * -1.0   # this value has to be negative

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
                    if cb_txt == 'Custom':
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
                    else:
                        self.ui.cutz_entry.set_value(self.old_cutz)

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

    def on_apply_param_to_all_clicked(self):
        if self.ui.geo_tools_table.rowCount() == 0:
            # there is no tool in tool table so we can't save the GUI elements values to storage
            log.debug("FlatCAMGeometry.gui_form_to_storage() --> no tool in Tools Table, aborting.")
            return

        self.ui_disconnect()

        row = self.ui.geo_tools_table.currentRow()
        if row < 0:
            row = 0

        # store all the data associated with the row parameter to the self.tools storage
        tooldia_item = float(self.ui.geo_tools_table.item(row, 1).text())
        offset_item = self.ui.geo_tools_table.cellWidget(row, 2).currentText()
        type_item = self.ui.geo_tools_table.cellWidget(row, 3).currentText()
        tool_type_item = self.ui.geo_tools_table.cellWidget(row, 4).currentText()

        offset_value_item = float(self.ui.tool_offset_entry.get_value())

        # this new dict will hold the actual useful data, another dict that is the value of key 'data'
        temp_tools = {}
        temp_dia = {}
        temp_data = {}

        for tooluid_key, tooluid_value in self.tools.items():
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

        self.tools.clear()
        self.tools = deepcopy(temp_tools)
        temp_tools.clear()

        self.ui_connect()

    def gui_form_to_storage(self):
        if self.ui.geo_tools_table.rowCount() == 0:
            # there is no tool in tool table so we can't save the GUI elements values to storage
            log.debug("FlatCAMGeometry.gui_form_to_storage() --> no tool in Tools Table, aborting.")
            return

        self.ui_disconnect()
        widget_changed = self.sender()
        try:
            widget_idx = self.ui.grid3.indexOf(widget_changed)
        except Exception as e:
            return

        # those are the indexes for the V-Tip Dia and V-Tip Angle, if edited calculate the new Cut Z
        if widget_idx == 1 or widget_idx == 3:
            self.update_cutz()

        # the original connect() function of the OptionalInputSelection is no longer working because of the
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

        offset_value_item = float(self.ui.tool_offset_entry.get_value())

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

    def update_common_param_in_storage(self):
        for tooluid_value in self.tools.values():
            tooluid_value['data']['ppname_g'] = self.ui.pp_geometry_name_cb.get_value()

    def select_tools_table_row(self, row, clearsel=None):
        if clearsel:
            self.ui.geo_tools_table.clearSelection()

        if self.ui.geo_tools_table.rowCount() > 0:
            # self.ui.geo_tools_table.item(row, 0).setSelected(True)
            self.ui.geo_tools_table.setCurrentItem(self.ui.geo_tools_table.item(row, 0))

    def export_dxf(self):
        units = self.app.defaults['units'].upper()
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
                elem = list()
                txt = ''

                for column in range(0, self.ui.geo_tools_table.columnCount()):
                    try:
                        txt = self.ui.geo_tools_table.item(x.row(), column).text()
                    except AttributeError:
                        try:
                            txt = self.ui.geo_tools_table.cellWidget(x.row(), column).currentText()
                        except AttributeError:
                            pass
                    elem.append(txt)
                table_tools_items.append(deepcopy(elem))
                # table_tools_items.append([self.ui.geo_tools_table.item(x.row(), column).text()
                #                           for column in range(0, self.ui.geo_tools_table.columnCount())])
        else:
            for x in self.ui.geo_tools_table.selectedItems():
                r = []
                txt = ''

                # the last 2 columns for single-geo geometry are irrelevant and create problems reading
                # so we don't read them
                for column in range(0, self.ui.geo_tools_table.columnCount() - 2):
                    # the columns have items that have text but also have items that are widgets
                    # for which the text they hold has to be read differently
                    try:
                        txt = self.ui.geo_tools_table.item(x.row(), column).text()
                    except AttributeError:
                        try:
                            txt = self.ui.geo_tools_table.cellWidget(x.row(), column).currentText()
                        except AttributeError:
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

        if 'marlin' in current_pp.lower() or 'custom' in current_pp.lower():
            self.ui.fr_rapidlabel.show()
            self.ui.feedrate_rapid_entry.show()
        else:
            self.ui.fr_rapidlabel.hide()
            self.ui.feedrate_rapid_entry.hide()

        if 'laser' in current_pp.lower():
            self.ui.cutzlabel.hide()
            self.ui.cutz_entry.hide()
            try:
                self.ui.mpass_cb.hide()
                self.ui.maxdepth_entry.hide()
            except AttributeError:
                pass

            if 'marlin' in current_pp.lower():
                self.ui.travelzlabel.setText('%s:' % _("Focus Z"))
                self.ui.endz_label.show()
                self.ui.endz_entry.show()
            else:
                self.ui.travelzlabel.hide()
                self.ui.travelz_entry.hide()

                self.ui.endz_label.hide()
                self.ui.endz_entry.hide()

            try:
                self.ui.frzlabel.hide()
                self.ui.feedrate_z_entry.hide()
            except AttributeError:
                pass

            self.ui.dwell_cb.hide()
            self.ui.dwelltime_entry.hide()

            self.ui.spindle_label.setText('%s:' % _("Laser Power"))

            try:
                self.ui.tool_offset_label.hide()
                self.ui.offset_entry.hide()
            except AttributeError:
                pass
        else:
            self.ui.cutzlabel.show()
            self.ui.cutz_entry.show()
            try:
                self.ui.mpass_cb.show()
                self.ui.maxdepth_entry.show()
            except AttributeError:
                pass

            self.ui.travelzlabel.setText('%s:' % _('Travel Z'))

            self.ui.travelzlabel.show()
            self.ui.travelz_entry.show()

            self.ui.endz_label.show()
            self.ui.endz_entry.show()

            try:
                self.ui.frzlabel.show()
                self.ui.feedrate_z_entry.show()
            except AttributeError:
                pass
            self.ui.dwell_cb.show()
            self.ui.dwelltime_entry.show()

            self.ui.spindle_label.setText('%s:' % _('Spindle speed'))

            try:
                self.ui.tool_offset_lbl.show()
                self.ui.offset_entry.show()
            except AttributeError:
                pass

    def on_generatecnc_button_click(self, *args):
        log.debug("Generating CNCJob from Geometry ...")
        self.app.report_usage("geometry_on_generatecnc_button")

        # this reads the values in the UI form to the self.options dictionary
        self.read_form()

        self.sel_tools = dict()

        try:
            if self.special_group:
                self.app.inform.emit(
                    '[WARNING_NOTCL] %s %s %s.' %
                    (_("This Geometry can't be processed because it is"), str(self.special_group), _("geometry"))
                )
                return
        except AttributeError:
            pass

        # test to see if we have tools available in the tool table
        if self.ui.geo_tools_table.selectedItems():
            for x in self.ui.geo_tools_table.selectedItems():
                # try:
                #     tooldia = float(self.ui.geo_tools_table.item(x.row(), 1).text())
                # except ValueError:
                #     # try to convert comma to decimal point. if it's still not working error message and return
                #     try:
                #         tooldia = float(self.ui.geo_tools_table.item(x.row(), 1).text().replace(',', '.'))
                #     except ValueError:
                #         self.app.inform.emit('[ERROR_NOTCL] %s' %
                #                              _("Wrong value format entered, use a number."))
                #         return
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
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed. No tool selected in the tool table ..."))

    def mtool_gen_cncjob(self, outname=None, tools_dict=None, tools_in_use=None, segx=None, segy=None,
                         plot=True, use_thread=True):
        """
        Creates a multi-tool CNCJob out of this Geometry object.
        The actual work is done by the target FlatCAMCNCjob object's
        `generate_from_geometry_2()` method.

        :param tools_dict: a dictionary that holds the whole data needed to create the Gcode
        (including the solid_geometry)

        :param tools_in_use: the tools that are used, needed by some preprocessors
        :type list of lists, each list in the list is made out of row elements of tools table from GUI

        :param segx: number of segments on the X axis, for auto-levelling
        :param segy: number of segments on the Y axis, for auto-levelling
        :param plot: if True the generated object will be plotted; if False will not be plotted
        :param use_thread: if True use threading
        :return: None
        """

        # use the name of the first tool selected in self.geo_tools_table which has the diameter passed as tool_dia
        outname = "%s_%s" % (self.options["name"], 'cnc') if outname is None else outname

        tools_dict = self.sel_tools if tools_dict is None else tools_dict
        tools_in_use = tools_in_use if tools_in_use is not None else self.get_selected_tools_table_items()
        segx = segx if segx is not None else float(self.app.defaults['geometry_segx'])
        segy = segy if segy is not None else float(self.app.defaults['geometry_segy'])

        try:
            xmin = self.options['xmin']
            ymin = self.options['ymin']
            xmax = self.options['xmax']
            ymax = self.options['ymax']
        except Exception as e:
            log.debug("FlatCAMObj.FlatCAMGeometry.mtool_gen_cncjob() --> %s\n" % str(e))

            msg = '[ERROR] %s' % _("An internal error has occurred. See shell.\n")
            msg += '%s %s' % ('FlatCAMObj.FlatCAMGeometry.mtool_gen_cncjob() -->', str(e))
            msg += traceback.format_exc()
            self.app.inform.emit(msg)
            return

        # Object initialization function for app.new_object()
        # RUNNING ON SEPARATE THREAD!
        def job_init_single_geometry(job_obj, app_obj):
            log.debug("Creating a CNCJob out of a single-geometry")
            assert isinstance(job_obj, FlatCAMCNCjob), \
                "Initializer expected a FlatCAMCNCjob, got %s" % type(job_obj)

            job_obj.options['xmin'] = xmin
            job_obj.options['ymin'] = ymin
            job_obj.options['xmax'] = xmax
            job_obj.options['ymax'] = ymax

            # count the tools
            tool_cnt = 0

            dia_cnc_dict = dict()

            # this turn on the FlatCAMCNCJob plot for multiple tools
            job_obj.multitool = True
            job_obj.multigeo = False
            job_obj.cnc_tools.clear()

            job_obj.options['Tools_in_use'] = tools_in_use
            job_obj.segx = segx if segx else float(self.app.defaults["geometry_segx"])
            job_obj.segy = segy if segy else float(self.app.defaults["geometry_segy"])

            job_obj.z_pdepth = float(self.app.defaults["geometry_z_pdepth"])
            job_obj.feedrate_probe = float(self.app.defaults["geometry_feedrate_probe"])

            for tooluid_key in list(tools_dict.keys()):
                tool_cnt += 1

                dia_cnc_dict = deepcopy(tools_dict[tooluid_key])
                tooldia_val = float('%.*f' % (self.decimals, float(tools_dict[tooluid_key]['tooldia'])))
                dia_cnc_dict.update({
                    'tooldia': tooldia_val
                })

                if dia_cnc_dict['offset'] == 'in':
                    tool_offset = -dia_cnc_dict['tooldia'] / 2
                elif dia_cnc_dict['offset'].lower() == 'out':
                    tool_offset = dia_cnc_dict['tooldia'] / 2
                elif dia_cnc_dict['offset'].lower() == 'custom':
                    try:
                        offset_value = float(self.ui.tool_offset_entry.get_value())
                    except ValueError:
                        # try to convert comma to decimal point. if it's still not working error message and return
                        try:
                            offset_value = float(self.ui.tool_offset_entry.get_value().replace(',', '.'))
                        except ValueError:
                            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Wrong value format entered, use a number."))
                            return
                    if offset_value:
                        tool_offset = float(offset_value)
                    else:
                        self.app.inform.emit(
                            '[WARNING] %s' % _("Tool Offset is selected in Tool Table but no value is provided.\n"
                                               "Add a Tool Offset or change the Offset Type.")
                        )
                        return
                else:
                    tool_offset = 0.0

                dia_cnc_dict.update({
                    'offset_value': tool_offset
                })

                z_cut = tools_dict[tooluid_key]['data']["cutz"]
                z_move = tools_dict[tooluid_key]['data']["travelz"]
                feedrate = tools_dict[tooluid_key]['data']["feedrate"]
                feedrate_z = tools_dict[tooluid_key]['data']["feedrate_z"]
                feedrate_rapid = tools_dict[tooluid_key]['data']["feedrate_rapid"]
                multidepth = tools_dict[tooluid_key]['data']["multidepth"]
                extracut = tools_dict[tooluid_key]['data']["extracut"]
                extracut_length = tools_dict[tooluid_key]['data']["extracut_length"]
                depthpercut = tools_dict[tooluid_key]['data']["depthperpass"]
                toolchange = tools_dict[tooluid_key]['data']["toolchange"]
                toolchangez = tools_dict[tooluid_key]['data']["toolchangez"]
                toolchangexy = tools_dict[tooluid_key]['data']["toolchangexy"]
                startz = tools_dict[tooluid_key]['data']["startz"]
                endz = tools_dict[tooluid_key]['data']["endz"]
                spindlespeed = tools_dict[tooluid_key]['data']["spindlespeed"]
                dwell = tools_dict[tooluid_key]['data']["dwell"]
                dwelltime = tools_dict[tooluid_key]['data']["dwelltime"]
                pp_geometry_name = tools_dict[tooluid_key]['data']["ppname_g"]

                spindledir = self.app.defaults['geometry_spindledir']
                tool_solid_geometry = self.solid_geometry

                job_obj.coords_decimals = self.app.defaults["cncjob_coords_decimals"]
                job_obj.fr_decimals = self.app.defaults["cncjob_fr_decimals"]

                # Propagate options
                job_obj.options["tooldia"] = tooldia_val
                job_obj.options['type'] = 'Geometry'
                job_obj.options['tool_dia'] = tooldia_val

                # it seems that the tolerance needs to be a lot lower value than 0.01 and it was hardcoded initially
                # to a value of 0.0005 which is 20 times less than 0.01
                tol = float(self.app.defaults['global_tolerance']) / 20
                res = job_obj.generate_from_geometry_2(
                    self, tooldia=tooldia_val, offset=tool_offset, tolerance=tol,
                    z_cut=z_cut, z_move=z_move,
                    feedrate=feedrate, feedrate_z=feedrate_z, feedrate_rapid=feedrate_rapid,
                    spindlespeed=spindlespeed, spindledir=spindledir, dwell=dwell, dwelltime=dwelltime,
                    multidepth=multidepth, depthpercut=depthpercut,
                    extracut=extracut, extracut_length=extracut_length, startz=startz, endz=endz,
                    toolchange=toolchange, toolchangez=toolchangez, toolchangexy=toolchangexy,
                    pp_geometry_name=pp_geometry_name,
                    tool_no=tool_cnt)

                if res == 'fail':
                    log.debug("FlatCAMGeometry.mtool_gen_cncjob() --> generate_from_geometry2() failed")
                    return 'fail'
                else:
                    dia_cnc_dict['gcode'] = res

                # tell gcode_parse from which point to start drawing the lines depending on what kind of
                # object is the source of gcode
                job_obj.toolchange_xy_type = "geometry"

                self.app.inform.emit('[success] %s' % _("G-Code parsing in progress..."))
                dia_cnc_dict['gcode_parsed'] = job_obj.gcode_parse()
                self.app.inform.emit('[success] %s' % _("G-Code parsing finished..."))

                # TODO this serve for bounding box creation only; should be optimized
                # commented this; there is no need for the actual GCode geometry - the original one will serve as well
                # for bounding box values
                # dia_cnc_dict['solid_geometry'] = cascaded_union([geo['geom'] for geo in dia_cnc_dict['gcode_parsed']])
                try:
                    dia_cnc_dict['solid_geometry'] = tool_solid_geometry
                    self.app.inform.emit('[success] %s...' % _("Finished G-Code processing"))
                except Exception as e:
                    self.app.inform.emit('[ERROR] %s: %s' % (_("G-Code processing failed with error"), str(e)))

                job_obj.cnc_tools.update({
                    tooluid_key: deepcopy(dia_cnc_dict)
                })
                dia_cnc_dict.clear()

        # Object initialization function for app.new_object()
        # RUNNING ON SEPARATE THREAD!
        def job_init_multi_geometry(job_obj, app_obj):
            log.debug("Creating a CNCJob out of a multi-geometry")
            assert isinstance(job_obj, FlatCAMCNCjob), \
                "Initializer expected a FlatCAMCNCjob, got %s" % type(job_obj)

            current_uid = int(1)

            job_obj.options['xmin'] = xmin
            job_obj.options['ymin'] = ymin
            job_obj.options['xmax'] = xmax
            job_obj.options['ymax'] = ymax

            # count the tools
            tool_cnt = 0

            dia_cnc_dict = dict()

            # this turn on the FlatCAMCNCJob plot for multiple tools
            job_obj.multitool = True
            job_obj.multigeo = True
            job_obj.cnc_tools.clear()

            job_obj.options['Tools_in_use'] = tools_in_use
            job_obj.segx = segx if segx else float(self.app.defaults["geometry_segx"])
            job_obj.segy = segy if segy else float(self.app.defaults["geometry_segy"])

            job_obj.z_pdepth = float(self.app.defaults["geometry_z_pdepth"])
            job_obj.feedrate_probe = float(self.app.defaults["geometry_feedrate_probe"])

            # make sure that trying to make a CNCJob from an empty file is not creating an app crash
            if not self.solid_geometry:
                a = 0
                for tooluid_key in self.tools:
                    if self.tools[tooluid_key]['solid_geometry'] is None:
                        a += 1
                if a == len(self.tools):
                    self.app.inform.emit('[ERROR_NOTCL] %s...' % _('Cancelled. Empty file, it has no geometry'))
                    return 'fail'

            for tooluid_key in list(tools_dict.keys()):
                tool_cnt += 1
                dia_cnc_dict = deepcopy(tools_dict[tooluid_key])
                tooldia_val = float('%.*f' % (self.decimals, float(tools_dict[tooluid_key]['tooldia'])))

                dia_cnc_dict.update({
                    'tooldia': tooldia_val
                })

                # find the tool_dia associated with the tooluid_key
                # search in the self.tools for the sel_tool_dia and when found see what tooluid has
                # on the found tooluid in self.tools we also have the solid_geometry that interest us
                for k, v in self.tools.items():
                    if float('%.*f' % (self.decimals, float(v['tooldia']))) == tooldia_val:
                        current_uid = int(k)
                        break

                if dia_cnc_dict['offset'] == 'in':
                    tool_offset = -tooldia_val / 2
                elif dia_cnc_dict['offset'].lower() == 'out':
                    tool_offset = tooldia_val / 2
                elif dia_cnc_dict['offset'].lower() == 'custom':
                    offset_value = float(self.ui.tool_offset_entry.get_value())
                    if offset_value:
                        tool_offset = float(offset_value)
                    else:
                        self.app.inform.emit('[WARNING] %s' %
                                             _("Tool Offset is selected in Tool Table but "
                                               "no value is provided.\n"
                                               "Add a Tool Offset or change the Offset Type."))
                        return
                else:
                    tool_offset = 0.0

                dia_cnc_dict.update({
                    'offset_value': tool_offset
                })

                z_cut = tools_dict[tooluid_key]['data']["cutz"]
                z_move = tools_dict[tooluid_key]['data']["travelz"]
                feedrate = tools_dict[tooluid_key]['data']["feedrate"]
                feedrate_z = tools_dict[tooluid_key]['data']["feedrate_z"]
                feedrate_rapid = tools_dict[tooluid_key]['data']["feedrate_rapid"]
                multidepth = tools_dict[tooluid_key]['data']["multidepth"]
                extracut = tools_dict[tooluid_key]['data']["extracut"]
                extracut_length = tools_dict[tooluid_key]['data']["extracut_length"]
                depthpercut = tools_dict[tooluid_key]['data']["depthperpass"]
                toolchange = tools_dict[tooluid_key]['data']["toolchange"]
                toolchangez = tools_dict[tooluid_key]['data']["toolchangez"]
                toolchangexy = tools_dict[tooluid_key]['data']["toolchangexy"]
                startz = tools_dict[tooluid_key]['data']["startz"]
                endz = tools_dict[tooluid_key]['data']["endz"]
                spindlespeed = tools_dict[tooluid_key]['data']["spindlespeed"]
                dwell = tools_dict[tooluid_key]['data']["dwell"]
                dwelltime = tools_dict[tooluid_key]['data']["dwelltime"]
                pp_geometry_name = tools_dict[tooluid_key]['data']["ppname_g"]

                spindledir = self.app.defaults['geometry_spindledir']
                tool_solid_geometry = self.tools[current_uid]['solid_geometry']

                job_obj.coords_decimals = self.app.defaults["cncjob_coords_decimals"]
                job_obj.fr_decimals = self.app.defaults["cncjob_fr_decimals"]

                # Propagate options
                job_obj.options["tooldia"] = tooldia_val
                job_obj.options['type'] = 'Geometry'
                job_obj.options['tool_dia'] = tooldia_val

                # it seems that the tolerance needs to be a lot lower value than 0.01 and it was hardcoded initially
                # to a value of 0.0005 which is 20 times less than 0.01
                tol = float(self.app.defaults['global_tolerance']) / 20
                res = job_obj.generate_from_multitool_geometry(
                    tool_solid_geometry, tooldia=tooldia_val, offset=tool_offset,
                    tolerance=tol, z_cut=z_cut, z_move=z_move,
                    feedrate=feedrate, feedrate_z=feedrate_z, feedrate_rapid=feedrate_rapid,
                    spindlespeed=spindlespeed, spindledir=spindledir, dwell=dwell, dwelltime=dwelltime,
                    multidepth=multidepth, depthpercut=depthpercut,
                    extracut=extracut, extracut_length=extracut_length, startz=startz, endz=endz,
                    toolchange=toolchange, toolchangez=toolchangez, toolchangexy=toolchangexy,
                    pp_geometry_name=pp_geometry_name,
                    tool_no=tool_cnt)

                if res == 'fail':
                    log.debug("FlatCAMGeometry.mtool_gen_cncjob() --> generate_from_geometry2() failed")
                    return 'fail'
                else:
                    dia_cnc_dict['gcode'] = res

                self.app.inform.emit('[success] %s' % _("G-Code parsing in progress..."))
                dia_cnc_dict['gcode_parsed'] = job_obj.gcode_parse()
                self.app.inform.emit('[success] %s' % _("G-Code parsing finished..."))

                # TODO this serve for bounding box creation only; should be optimized
                # commented this; there is no need for the actual GCode geometry - the original one will serve as well
                # for bounding box values
                # geo_for_bound_values = cascaded_union([
                #     geo['geom'] for geo in dia_cnc_dict['gcode_parsed'] if geo['geom'].is_valid is True
                # ])
                try:
                    dia_cnc_dict['solid_geometry'] = deepcopy(tool_solid_geometry)
                    self.app.inform.emit('[success] %s' % _("Finished G-Code processing..."))
                except Exception as e:
                    self.app.inform.emit('[ERROR] %s: %s' % (_("G-Code processing failed with error"), str(e)))

                # tell gcode_parse from which point to start drawing the lines depending on what kind of
                # object is the source of gcode
                job_obj.toolchange_xy_type = "geometry"

                job_obj.cnc_tools.update({
                    tooluid_key: deepcopy(dia_cnc_dict)
                })
                dia_cnc_dict.clear()

        if use_thread:
            # To be run in separate thread
            def job_thread(app_obj):
                if self.multigeo is False:
                    with self.app.proc_container.new(_("Generating CNC Code")):
                        if app_obj.new_object("cncjob", outname, job_init_single_geometry, plot=plot) != 'fail':
                            app_obj.inform.emit('[success] %s: %s' % (_("CNCjob created"), outname))
                else:
                    with self.app.proc_container.new(_("Generating CNC Code")):
                        if app_obj.new_object("cncjob", outname, job_init_multi_geometry) != 'fail':
                            app_obj.inform.emit('[success] %s: %s' % (_("CNCjob created"), outname))

            # Create a promise with the name
            self.app.collection.promise(outname)
            # Send to worker
            self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})
        else:
            if self.solid_geometry:
                self.app.new_object("cncjob", outname, job_init_single_geometry, plot=plot)
            else:
                self.app.new_object("cncjob", outname, job_init_multi_geometry, plot=plot)

    def generatecncjob(
            self, outname=None,
            dia=None, offset=None,
            z_cut=None, z_move=None,
            feedrate=None, feedrate_z=None, feedrate_rapid=None,
            spindlespeed=None, dwell=None, dwelltime=None,
            multidepth=None, depthperpass=None,
            toolchange=None, toolchangez=None, toolchangexy=None,
            extracut=None, extracut_length=None, startz=None, endz=None,
            pp=None,
            segx=None, segy=None,
            use_thread=True,
            plot=True):
        """
        Only used for TCL Command.
        Creates a CNCJob out of this Geometry object. The actual
        work is done by the target camlib.CNCjob
        `generate_from_geometry_2()` method.

        :param z_cut: Cut depth (negative)
        :param z_move: Hight of the tool when travelling (not cutting)
        :param feedrate: Feed rate while cutting on X - Y plane
        :param feedrate_z: Feed rate while cutting on Z plane
        :param feedrate_rapid: Feed rate while moving with rapids
        :param dia: Tool diameter
        :param outname: Name of the new object
        :param spindlespeed: Spindle speed (RPM)
        :param pp Name of the preprocessor
        :return: None
        """

        tooldia = dia if dia else float(self.options["cnctooldia"])
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
        extracut_length = extracut_length if extracut_length is not None else float(self.options["extracut_length"])

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

        ppname_g = pp if pp else self.options["ppname_g"]

        # Object initialization function for app.new_object()
        # RUNNING ON SEPARATE THREAD!
        def job_init(job_obj, app_obj):
            assert isinstance(job_obj, FlatCAMCNCjob), "Initializer expected a FlatCAMCNCjob, got %s" % type(job_obj)

            # Propagate options
            job_obj.options["tooldia"] = tooldia

            job_obj.coords_decimals = self.app.defaults["cncjob_coords_decimals"]
            job_obj.fr_decimals = self.app.defaults["cncjob_fr_decimals"]

            job_obj.options['type'] = 'Geometry'
            job_obj.options['tool_dia'] = tooldia

            job_obj.segx = segx
            job_obj.segy = segy

            job_obj.z_pdepth = float(self.options["z_pdepth"])
            job_obj.feedrate_probe = float(self.options["feedrate_probe"])

            job_obj.options['xmin'] = self.options['xmin']
            job_obj.options['ymin'] = self.options['ymin']
            job_obj.options['xmax'] = self.options['xmax']
            job_obj.options['ymax'] = self.options['ymax']

            # it seems that the tolerance needs to be a lot lower value than 0.01 and it was hardcoded initially
            # to a value of 0.0005 which is 20 times less than 0.01
            tol = float(self.app.defaults['global_tolerance']) / 20
            job_obj.generate_from_geometry_2(
                self, tooldia=tooldia, offset=offset, tolerance=tol,
                z_cut=z_cut, z_move=z_move,
                feedrate=feedrate, feedrate_z=feedrate_z, feedrate_rapid=feedrate_rapid,
                spindlespeed=spindlespeed, dwell=dwell, dwelltime=dwelltime,
                multidepth=multidepth, depthpercut=depthperpass,
                toolchange=toolchange, toolchangez=toolchangez, toolchangexy=toolchangexy,
                extracut=extracut, extracut_length=extracut_length, startz=startz, endz=endz,
                pp_geometry_name=ppname_g
            )

            # tell gcode_parse from which point to start drawing the lines depending on what kind of object is the
            # source of gcode
            job_obj.toolchange_xy_type = "geometry"
            job_obj.gcode_parse()
            self.app.inform.emit('[success] %s' % _("Finished G-Code processing..."))

        if use_thread:
            # To be run in separate thread
            def job_thread(app_obj):
                with self.app.proc_container.new(_("Generating CNC Code")):
                    app_obj.new_object("cncjob", outname, job_init, plot=plot)
                    app_obj.inform.emit('[success] %s: %s' % (_("CNCjob created")), outname)

            # Create a promise with the name
            self.app.collection.promise(outname)
            # Send to worker
            self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})
        else:
            self.app.new_object("cncjob", outname, job_init, plot=plot)

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
        log.debug("FlatCAMObj.FlatCAMGeometry.scale()")

        try:
            xfactor = float(xfactor)
        except Exception:
            self.app.inform.emit('[ERROR_NOTCL] %s' %  _("Scale factor has to be a number: integer or float."))
            return

        if yfactor is None:
            yfactor = xfactor
        else:
            try:
                yfactor = float(yfactor)
            except Exception:
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("Scale factor has to be a number: integer or float."))
                return

        if xfactor == 1 and yfactor == 1:
            return

        if point is None:
            px = 0
            py = 0
        else:
            px, py = point

        self.geo_len = 0
        self.old_disp_number = 0
        self.el_count = 0

        def scale_recursion(geom):
            if type(geom) is list:
                geoms = list()
                for local_geom in geom:
                    geoms.append(scale_recursion(local_geom))
                return geoms
            else:
                try:
                    self.el_count += 1
                    disp_number = int(np.interp(self.el_count, [0, self.geo_len], [0, 100]))
                    if self.old_disp_number < disp_number <= 100:
                        self.app.proc_container.update_view_text(' %d%%' % disp_number)
                        self.old_disp_number = disp_number

                    return affinity.scale(geom, xfactor, yfactor, origin=(px, py))
                except AttributeError:
                    return geom

        if self.multigeo is True:
            for tool in self.tools:
                # variables to display the percentage of work done
                self.geo_len = 0
                try:
                    for g in self.tools[tool]['solid_geometry']:
                        self.geo_len += 1
                except TypeError:
                    self.geo_len = 1
                self.old_disp_number = 0
                self.el_count = 0

                self.tools[tool]['solid_geometry'] = scale_recursion(self.tools[tool]['solid_geometry'])

        try:
            # variables to display the percentage of work done
            self.geo_len = 0
            try:
                self.geo_len = len(self.solid_geometry)
            except TypeError:
                self.geo_len = 1
            self.old_disp_number = 0
            self.el_count = 0

            self.solid_geometry = scale_recursion(self.solid_geometry)
        except AttributeError:
            self.solid_geometry = []
            return

        self.app.proc_container.new_text = ''
        self.app.inform.emit('[success] %s' % _("Geometry Scale done."))

    def offset(self, vect):
        """
        Offsets all geometry by a given vector/

        :param vect: (x, y) vector by which to offset the object's geometry.
        :type vect: tuple
        :return: None
        :rtype: None
        """
        log.debug("FlatCAMObj.FlatCAMGeometry.offset()")

        try:
            dx, dy = vect
        except TypeError:
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("An (x,y) pair of values are needed. "
                                   "Probable you entered only one value in the Offset field.")
                                 )
            return

        if dx == 0 and dy == 0:
            return

        self.geo_len = 0
        self.old_disp_number = 0
        self.el_count = 0

        def translate_recursion(geom):
            if type(geom) is list:
                geoms = list()
                for local_geom in geom:
                    geoms.append(translate_recursion(local_geom))
                return geoms
            else:
                try:
                    self.el_count += 1
                    disp_number = int(np.interp(self.el_count, [0, self.geo_len], [0, 100]))
                    if self.old_disp_number < disp_number <= 100:
                        self.app.proc_container.update_view_text(' %d%%' % disp_number)
                        self.old_disp_number = disp_number

                    return affinity.translate(geom, xoff=dx, yoff=dy)
                except AttributeError:
                    return geom

        if self.multigeo is True:
            for tool in self.tools:
                # variables to display the percentage of work done
                self.geo_len = 0
                try:
                    for g in self.tools[tool]['solid_geometry']:
                        self.geo_len += 1
                except TypeError:
                    self.geo_len = 1
                self.old_disp_number = 0
                self.el_count = 0

                self.tools[tool]['solid_geometry'] = translate_recursion(self.tools[tool]['solid_geometry'])

        # variables to display the percentage of work done
        self.geo_len = 0
        try:
            for g in self.solid_geometry:
                self.geo_len += 1
        except TypeError:
            self.geo_len = 1
        self.old_disp_number = 0
        self.el_count = 0

        self.solid_geometry = translate_recursion(self.solid_geometry)

        self.app.proc_container.new_text = ''
        self.app.inform.emit('[success] %s' % _("Geometry Offset done."))

    def convert_units(self, units):
        log.debug("FlatCAMObj.FlatCAMGeometry.convert_units()")

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
                self.app.inform.emit('[ERROR] %s' %
                                     _("The Toolchange X,Y field in Edit -> Preferences "
                                       "has to be in the format (x, y)\n"
                                       "but now there is only one value, not two.")
                                     )
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
                        dia_value = float('%.*f' % (self.decimals, dia_value))
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
                                custom_offset = float(self.ui.tool_offset_entry.get_value().replace(',', '.'))
                            except ValueError:
                                self.app.inform.emit('[ERROR_NOTCL] %s' %
                                                     _("Wrong value format entered, use a number."))
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
        try:
            self.ui.addtool_entry.returnPressed.disconnect()
        except TypeError:
            pass
        tooldia = self.ui.addtool_entry.get_value()
        if tooldia:
            tooldia *= factor
            tooldia = float('%.*f' % (self.decimals, tooldia))

            self.ui.addtool_entry.set_value(tooldia)
        self.ui.addtool_entry.returnPressed.connect(self.on_tool_add)

        return factor

    def plot_element(self, element, color=None, visible=None):

        if color is None:
            color = '#FF0000FF'

        visible = visible if visible else self.options['plot']
        try:
            for sub_el in element:
                self.plot_element(sub_el, color=color)

        except TypeError:  # Element is not iterable...
            # if self.app.is_legacy is False:
            self.add_shape(shape=element, color=color, visible=visible, layer=0)

    def plot(self, visible=None, kind=None):
        """
        Plot the object.

        :param visible: Controls if the added shape is visible of not
        :param kind: added so there is no error when a project is loaded and it has both geometry and CNCJob, because
        CNCJob require the 'kind' parameter. Perhaps the FlatCAMObj.plot() has to be rewrited
        :return:
        """

        # Does all the required setup and returns False
        # if the 'ptint' option is set to False.
        if not FlatCAMObj.plot(self):
            return

        try:
            # plot solid geometries found as members of self.tools attribute dict
            # for MultiGeo
            if self.multigeo is True:  # geo multi tool usage
                for tooluid_key in self.tools:
                    solid_geometry = self.tools[tooluid_key]['solid_geometry']
                    self.plot_element(solid_geometry, visible=visible,
                                      color=self.app.defaults["geometry_plot_line"])
            else:
                # plot solid geometry that may be an direct attribute of the geometry object
                # for SingleGeo
                if self.solid_geometry:
                    self.plot_element(self.solid_geometry, visible=visible,
                                      color=self.app.defaults["geometry_plot_line"])

            # self.plot_element(self.solid_geometry, visible=self.options['plot'])

            self.shapes.redraw()

        except (ObjectDeleted, AttributeError):
            self.shapes.clear(update=True)

    def on_plot_cb_click(self, *args):
        if self.muted_ui:
            return
        self.read_form_item('plot')
        self.plot()

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
        # cw = self.sender()
        # cw_index = self.ui.geo_tools_table.indexAt(cw.pos())
        # cw_row = cw_index.row()
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

    def merge(self, geo_list, geo_final, multigeo=None):
        """
        Merges the geometry of objects in grb_list into
        the geometry of geo_final.

        :param geo_list: List of FlatCAMGerber Objects to join.
        :param geo_final: Destination FlatCAMGerber object.
        :param multigeo: if the merged geometry objects are of type MultiGeo
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
                        geo_final.options[option] = deepcopy(geo.options[option])
                    except Exception as e:
                        log.warning("Failed to copy option %s. Error: %s" % (str(option), str(e)))

            # Expand lists
            if type(geo) is list:
                FlatCAMGeometry.merge(self, geo_list=geo, geo_final=geo_final)
            # If not list, just append
            else:
                # merge solid_geometry, useful for singletool geometry, for multitool each is empty
                if multigeo is None or multigeo is False:
                    geo_final.multigeo = False
                    try:
                        geo_final.solid_geometry.append(deepcopy(geo.solid_geometry))
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

        # Iterable: descend into each item.
        try:
            for subo in o:
                pts += FlatCAMGeometry.get_pts(subo)

        # Non-iterable
        except TypeError:
            if o is not None:
                if type(o) == MultiPolygon:
                    for poly in o:
                        pts += FlatCAMGeometry.get_pts(poly)
                # ## Descend into .exerior and .interiors
                elif type(o) == Polygon:
                    pts += FlatCAMGeometry.get_pts(o.exterior)
                    for i in o.interiors:
                        pts += FlatCAMGeometry.get_pts(i)
                elif type(o) == MultiLineString:
                    for line in o:
                        pts += FlatCAMGeometry.get_pts(line)
                # ## Has .coords: list them.
                else:
                    pts += list(o.coords)
            else:
                return
        return pts


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

        self.decimals = self.app.decimals

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
                           'gcode_parsed': {} # dictionary holding the CNCJob geometry and type of geometry 
                           (cut or move)
                           'solid_geometry': []
                           },
                           ...
               }
            It is populated in the FlatCAMGeometry.mtool_gen_cncjob()
            BEWARE: I rely on the ordered nature of the Python 3.7 dictionary. Things might change ...
        '''
        self.cnc_tools = dict()

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
           it's done in camlib.CNCJob.generate_from_excellon_by_tool()
           BEWARE: I rely on the ordered nature of the Python 3.7 dictionary. Things might change ...
       '''
        self.exc_cnc_tools = dict()

        # flag to store if the CNCJob is part of a special group of CNCJob objects that can't be processed by the
        # default engine of FlatCAM. They generated by some of tools and are special cases of CNCJob objects.
        self.special_group = None

        # for now it show if the plot will be done for multi-tool CNCJob (True) or for single tool
        # (like the one in the TCL Command), False
        self.multitool = False

        # determine if the GCode was generated out of a Excellon object or a Geometry object
        self.origin_kind = None

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
        self.ser_attrs += ['options', 'kind', 'origin_kind', 'cnc_tools', 'exc_cnc_tools', 'multitool']

        if self.app.is_legacy is False:
            self.text_col = self.app.plotcanvas.new_text_collection()
            self.text_col.enabled = True
            self.annotation = self.app.plotcanvas.new_text_group(collection=self.text_col)

        self.gcode_editor_tab = None

        self.units_found = self.app.defaults['units']

    def build_ui(self):
        self.ui_disconnect()

        FlatCAMObj.build_ui(self)
        self.units = self.app.defaults['units'].upper()

        # if the FlatCAM object is Excellon don't build the CNC Tools Table but hide it
        self.ui.cnc_tools_table.hide()
        if self.cnc_tools:
            self.ui.cnc_tools_table.show()
            self.build_cnc_tools_table()

        self.ui.exc_cnc_tools_table.hide()
        if self.exc_cnc_tools:
            self.ui.exc_cnc_tools_table.show()
            self.build_excellon_cnc_tools()
        #
        self.ui_connect()

    def build_cnc_tools_table(self):
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

            dia_item = QtWidgets.QTableWidgetItem('%.*f' % (self.decimals, float(dia_value['tooldia'])))

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

            # ## REMEMBER: THIS COLUMN IS HIDDEN IN OBJECTUI.PY # ##
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

    def build_excellon_cnc_tools(self):
        tool_idx = 0

        n = len(self.exc_cnc_tools)
        self.ui.exc_cnc_tools_table.setRowCount(n)

        for tooldia_key, dia_value in self.exc_cnc_tools.items():

            tool_idx += 1
            row_no = tool_idx - 1

            id = QtWidgets.QTableWidgetItem('%d' % int(tool_idx))
            dia_item = QtWidgets.QTableWidgetItem('%.*f' % (self.decimals, float(tooldia_key)))
            nr_drills_item = QtWidgets.QTableWidgetItem('%d' % int(dia_value['nr_drills']))
            nr_slots_item = QtWidgets.QTableWidgetItem('%d' % int(dia_value['nr_slots']))
            cutz_item = QtWidgets.QTableWidgetItem('%.*f' % (self.decimals, float(dia_value['offset_z']) + self.z_cut))

            id.setFlags(QtCore.Qt.ItemIsEnabled)
            dia_item.setFlags(QtCore.Qt.ItemIsEnabled)
            nr_drills_item.setFlags(QtCore.Qt.ItemIsEnabled)
            nr_slots_item.setFlags(QtCore.Qt.ItemIsEnabled)
            cutz_item.setFlags(QtCore.Qt.ItemIsEnabled)

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
            tool_uid_item = QtWidgets.QTableWidgetItem(str(dia_value['tool']))
            if self.ui.plot_cb.isChecked():
                plot_item.setChecked(True)

            # TODO until the feature of individual plot for an Excellon tool is implemented
            plot_item.setDisabled(True)

            self.ui.exc_cnc_tools_table.setItem(row_no, 0, id)  # Tool name/id
            self.ui.exc_cnc_tools_table.setItem(row_no, 1, dia_item)  # Diameter
            self.ui.exc_cnc_tools_table.setItem(row_no, 2, nr_drills_item)  # Nr of drills
            self.ui.exc_cnc_tools_table.setItem(row_no, 3, nr_slots_item)  # Nr of slots

            # ## REMEMBER: THIS COLUMN IS HIDDEN IN OBJECTUI.PY # ##
            self.ui.exc_cnc_tools_table.setItem(row_no, 4, tool_uid_item)  # Tool unique ID)
            self.ui.exc_cnc_tools_table.setItem(row_no, 5, cutz_item)
            self.ui.exc_cnc_tools_table.setCellWidget(row_no, 6, plot_item)

        for row in range(tool_idx):
            self.ui.exc_cnc_tools_table.item(row, 0).setFlags(
                self.ui.exc_cnc_tools_table.item(row, 0).flags() ^ QtCore.Qt.ItemIsSelectable)

        self.ui.exc_cnc_tools_table.resizeColumnsToContents()
        self.ui.exc_cnc_tools_table.resizeRowsToContents()

        vertical_header = self.ui.exc_cnc_tools_table.verticalHeader()
        vertical_header.hide()
        self.ui.exc_cnc_tools_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        horizontal_header = self.ui.exc_cnc_tools_table.horizontalHeader()
        horizontal_header.setMinimumSectionSize(10)
        horizontal_header.setDefaultSectionSize(70)
        horizontal_header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        horizontal_header.resizeSection(0, 20)
        horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        horizontal_header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeToContents)

        horizontal_header.setSectionResizeMode(6, QtWidgets.QHeaderView.Fixed)

        # horizontal_header.setStretchLastSection(True)
        self.ui.exc_cnc_tools_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.ui.exc_cnc_tools_table.setColumnWidth(0, 20)
        self.ui.exc_cnc_tools_table.setColumnWidth(6, 17)

        self.ui.exc_cnc_tools_table.setMinimumHeight(self.ui.exc_cnc_tools_table.getHeight())
        self.ui.exc_cnc_tools_table.setMaximumHeight(self.ui.exc_cnc_tools_table.getHeight())

    def set_ui(self, ui):
        FlatCAMObj.set_ui(self, ui)

        FlatCAMApp.App.log.debug("FlatCAMCNCJob.set_ui()")

        assert isinstance(self.ui, CNCObjectUI), \
            "Expected a CNCObjectUI, got %s" % type(self.ui)

        self.units = self.app.defaults['units'].upper()
        self.units_found = self.app.defaults['units']

        # this signal has to be connected to it's slot before the defaults are populated
        # the decision done in the slot has to override the default value set bellow
        self.ui.toolchange_cb.toggled.connect(self.on_toolchange_custom_clicked)

        self.form_fields.update({
            "plot": self.ui.plot_cb,
            "tooldia": self.ui.tooldia_entry,
            "append": self.ui.append_text,
            "prepend": self.ui.prepend_text,
            "toolchange_macro": self.ui.toolchange_text,
            "toolchange_macro_enable": self.ui.toolchange_cb
        })

        # Fill form fields only on object create
        self.to_form()

        # this means that the object that created this CNCJob was an Excellon or Geometry
        try:
            if self.travel_distance:
                self.ui.t_distance_label.show()
                self.ui.t_distance_entry.setVisible(True)
                self.ui.t_distance_entry.setDisabled(True)
                self.ui.t_distance_entry.set_value('%.*f' % (self.decimals, float(self.travel_distance)))
                self.ui.units_label.setText(str(self.units).lower())
                self.ui.units_label.setDisabled(True)

                self.ui.t_time_label.show()
                self.ui.t_time_entry.setVisible(True)
                self.ui.t_time_entry.setDisabled(True)
                # if time is more than 1 then we have minutes, else we have seconds
                if self.routing_time > 1:
                    self.ui.t_time_entry.set_value('%.*f' % (self.decimals, math.ceil(float(self.routing_time))))
                    self.ui.units_time_label.setText('min')
                else:
                    time_r = self.routing_time * 60
                    self.ui.t_time_entry.set_value('%.*f' % (self.decimals, math.ceil(float(time_r))))
                    self.ui.units_time_label.setText('sec')
                self.ui.units_time_label.setDisabled(True)
        except AttributeError:
            pass

        if self.multitool is False:
            self.ui.tooldia_entry.show()
            self.ui.updateplot_button.show()
        else:
            self.ui.tooldia_entry.hide()
            self.ui.updateplot_button.hide()

        # set the kind of geometries are plotted by default with plot2() from camlib.CNCJob
        self.ui.cncplot_method_combo.set_value(self.app.defaults["cncjob_plot_kind"])

        try:
            self.ui.annotation_cb.stateChanged.disconnect(self.on_annotation_change)
        except (TypeError, AttributeError):
            pass
        self.ui.annotation_cb.stateChanged.connect(self.on_annotation_change)

        # set if to display text annotations
        self.ui.annotation_cb.set_value(self.app.defaults["cncjob_annotation"])

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
        self.ui.modify_gcode_button.clicked.connect(self.on_edit_code_click)

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
        except (TypeError, AttributeError):
            pass

    def on_updateplot_button_click(self, *args):
        """
        Callback for the "Updata Plot" button. Reads the form for updates
        and plots the object.
        """
        self.read_form()
        self.on_plot_kind_change()

    def on_plot_kind_change(self):
        kind = self.ui.cncplot_method_combo.get_value()

        def worker_task():
            with self.app.proc_container.new(_("Plotting...")):
                self.plot(kind=kind)

        self.app.worker_task.emit({'fcn': worker_task, 'params': []})

    def on_exportgcode_button_click(self, *args):
        self.app.report_usage("cncjob_on_exportgcode_button")

        self.read_form()
        name = self.app.collection.get_active().options['name']
        save_gcode = False

        if 'Roland' in self.pp_excellon_name or 'Roland' in self.pp_geometry_name:
            _filter_ = "RML1 Files (*.rol);;All Files (*.*)"
        elif 'hpgl' in self.pp_geometry_name:
            _filter_ = "HPGL Files (*.plt);;All Files (*.*)"
        else:
            save_gcode = True
            _filter_ = self.app.defaults['cncjob_save_filters']

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
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Export Machine Code cancelled ..."))
            return
        else:
            if save_gcode is True:
                used_extension = filename.rpartition('.')[2]
                self.update_filters(last_ext=used_extension, filter_string='cncjob_save_filters')

        new_name = os.path.split(str(filename))[1].rpartition('.')[0]
        self.ui.name_entry.set_value(new_name)
        self.on_name_activate(silent=True)

        preamble = str(self.ui.prepend_text.get_value())
        postamble = str(self.ui.append_text.get_value())

        gc = self.export_gcode(filename, preamble=preamble, postamble=postamble)
        if gc == 'fail':
            return

        if self.app.defaults["global_open_style"] is False:
            self.app.file_opened.emit("gcode", filename)
        self.app.file_saved.emit("gcode", filename)
        self.app.inform.emit('[success] %s: %s' %
                             (_("Machine Code file saved to"), filename))

    def on_edit_code_click(self, *args):
        self.app.proc_container.view.set_busy(_("Loading..."))

        preamble = str(self.ui.prepend_text.get_value())
        postamble = str(self.ui.append_text.get_value())

        gco = self.export_gcode(preamble=preamble, postamble=postamble, to_file=True)
        if gco == 'fail':
            return
        else:
            self.app.gcode_edited = gco

        self.gcode_editor_tab = TextEditor(app=self.app, plain_text=True)

        # add the tab if it was closed
        self.app.ui.plot_tab_area.addTab(self.gcode_editor_tab, '%s' % _("Code Editor"))
        self.gcode_editor_tab.setObjectName('code_editor_tab')

        # delete the absolute and relative position and messages in the infobar
        self.app.ui.position_label.setText("")
        self.app.ui.rel_position_label.setText("")

        # first clear previous text in text editor (if any)
        self.gcode_editor_tab.code_editor.clear()
        self.gcode_editor_tab.code_editor.setReadOnly(False)

        self.gcode_editor_tab.code_editor.completer_enable = False
        self.gcode_editor_tab.buttonRun.hide()

        # Switch plot_area to CNCJob tab
        self.app.ui.plot_tab_area.setCurrentWidget(self.gcode_editor_tab)

        self.gcode_editor_tab.t_frame.hide()
        # then append the text from GCode to the text editor
        try:
            self.gcode_editor_tab.code_editor.setPlainText(self.app.gcode_edited.getvalue())
            # for line in self.app.gcode_edited:
            #     QtWidgets.QApplication.processEvents()
            #
            #     proc_line = str(line).strip('\n')
            #     self.gcode_editor_tab.code_editor.append(proc_line)
        except Exception as e:
            log.debug('FlatCAMCNNJob.on_edit_code_click() -->%s' % str(e))
            self.app.inform.emit('[ERROR] %s %s' % ('FlatCAMCNNJob.on_edit_code_click() -->', str(e)))
            return

        self.gcode_editor_tab.code_editor.moveCursor(QtGui.QTextCursor.Start)

        self.gcode_editor_tab.handleTextChanged()
        self.gcode_editor_tab.t_frame.show()
        self.app.proc_container.view.set_idle()

        self.app.inform.emit('[success] %s...' % _('Loaded Machine Code into Code Editor'))

    def gcode_header(self, comment_start_symbol=None, comment_stop_symbol=None):
        """
        Will create a header to be added to all GCode files generated by FlatCAM

        :param comment_start_symbol: a symbol to be used as the first symbol in a comment
        :param comment_stop_symbol:  a symbol to be used as the last symbol in a comment
        :return: a string with a GCode header
        """

        log.debug("FlatCAMCNCJob.gcode_header()")
        time_str = "{:%A, %d %B %Y at %H:%M}".format(datetime.now())
        marlin = False
        hpgl = False
        probe_pp = False

        start_comment = comment_start_symbol if comment_start_symbol is not None else '('
        stop_comment = comment_stop_symbol if comment_stop_symbol is not None else ')'

        try:
            for key in self.cnc_tools:
                ppg = self.cnc_tools[key]['data']['ppname_g']
                if 'marlin' in ppg.lower() or 'repetier' in ppg.lower() :
                    marlin = True
                    break
                if ppg == 'hpgl':
                    hpgl = True
                    break
                if "toolchange_probe" in ppg.lower():
                    probe_pp = True
                    break
        except KeyError:
            # log.debug("FlatCAMCNCJob.gcode_header() error: --> %s" % str(e))
            pass

        try:
            if 'marlin' in self.options['ppname_e'].lower() or 'repetier' in self.options['ppname_e'].lower():
                marlin = True
        except KeyError:
            # log.debug("FlatCAMCNCJob.gcode_header(): --> There is no such self.option: %s" % str(e))
            pass

        try:
            if "toolchange_probe" in self.options['ppname_e'].lower():
                probe_pp = True
        except KeyError:
            # log.debug("FlatCAMCNCJob.gcode_header(): --> There is no such self.option: %s" % str(e))
            pass

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
            gcode = '%sG-CODE GENERATED BY FLATCAM v%s - www.flatcam.org - Version Date: %s%s\n' % \
                    (start_comment, str(self.app.version), str(self.app.version_date), stop_comment) + '\n'

            gcode += '%sName: ' % start_comment + str(self.options['name']) + '%s\n' % stop_comment
            gcode += '%sType: ' % start_comment + "G-code from " + str(self.options['type']) + '%s\n' % stop_comment

            # if str(p['options']['type']) == 'Excellon' or str(p['options']['type']) == 'Excellon Geometry':
            #     gcode += '(Tools in use: ' + str(p['options']['Tools_in_use']) + ')\n'

            gcode += '%sUnits: ' % start_comment + self.units.upper() + '%s\n' % stop_comment + "\n"
            gcode += '%sCreated on ' % start_comment + time_str + '%s\n' % stop_comment + '\n'

        return gcode

    def gcode_footer(self, end_command=None):
        """

        :param end_command: 'M02' or 'M30' - String
        :return:
        """
        if end_command:
            return end_command
        else:
            return 'M02'

    def export_gcode(self, filename=None, preamble='', postamble='', to_file=False):
        """
        This will save the GCode from the Gcode object to a file on the OS filesystem

        :param filename: filename for the GCode file
        :param preamble: a custom Gcode block to be added at the beginning of the Gcode file
        :param postamble: a custom Gcode block to be added at the end of the Gcode file
        :param to_file: if False then no actual file is saved but the app will know that a file was created
        :return: None
        """
        # gcode = ''
        # roland = False
        # hpgl = False
        # isel_icp = False

        include_header = True

        try:
            if self.special_group:
                self.app.inform.emit('[WARNING_NOTCL] %s %s %s.' %
                                     (_("This CNCJob object can't be processed because it is a"),
                                      str(self.special_group),
                                      _("CNCJob object")))
                return 'fail'
        except AttributeError:
            pass

        # if this dict is not empty then the object is a Geometry object
        if self.cnc_tools:
            first_key = next(iter(self.cnc_tools))
            include_header = self.app.preprocessors[self.cnc_tools[first_key]['data']['ppname_g']].include_header

        # if this dict is not empty then the object is an Excellon object
        if self.exc_cnc_tools:
            first_key = next(iter(self.exc_cnc_tools))
            include_header = self.app.preprocessors[self.exc_cnc_tools[first_key]['data']['ppname_e']].include_header

        # # detect if using Roland preprocessor
        # try:
        #     for key in self.cnc_tools:
        #         if self.cnc_tools[key]['data']['ppname_g'] == 'Roland_MDX_20':
        #             roland = True
        #             break
        # except Exception:
        #     try:
        #         for key in self.cnc_tools:
        #             if self.cnc_tools[key]['data']['ppname_e'] == 'Roland_MDX_20':
        #                 roland = True
        #                 break
        #     except Exception:
        #         pass
        #
        # # detect if using HPGL preprocessor
        # try:
        #     for key in self.cnc_tools:
        #         if self.cnc_tools[key]['data']['ppname_g'] == 'hpgl':
        #             hpgl = True
        #             break
        # except Exception:
        #     try:
        #         for key in self.cnc_tools:
        #             if self.cnc_tools[key]['data']['ppname_e'] == 'hpgl':
        #                 hpgl = True
        #                 break
        #     except Exception:
        #         pass
        #
        # # detect if using ISEL_ICP_CNC preprocessor
        # try:
        #     for key in self.cnc_tools:
        #         if 'ISEL_ICP' in self.cnc_tools[key]['data']['ppname_g'].upper():
        #             isel_icp = True
        #             break
        # except Exception:
        #     try:
        #         for key in self.cnc_tools:
        #             if 'ISEL_ICP' in self.cnc_tools[key]['data']['ppname_e'].upper():
        #                 isel_icp = True
        #                 break
        #     except Exception:
        #         pass

        # do not add gcode_header when using the Roland preprocessor, add it for every other preprocessor
        # if roland is False and hpgl is False and isel_icp is False:
        #     gcode = self.gcode_header()

        # do not add gcode_header when using the Roland, HPGL or ISEP_ICP_CNC preprocessor (or any other preprocessor
        # that has the include_header attribute set as False, add it for every other preprocessor
        # if include_header:
        #     gcode = self.gcode_header()
        # else:
        #     gcode = ''

        # # detect if using multi-tool and make the Gcode summation correctly for each case
        # if self.multitool is True:
        #     for tooluid_key in self.cnc_tools:
        #         for key, value in self.cnc_tools[tooluid_key].items():
        #             if key == 'gcode':
        #                 gcode += value
        #                 break
        # else:
        #     gcode += self.gcode

        # if roland is True:
        #     g = preamble + gcode + postamble
        # elif hpgl is True:
        #     g = self.gcode_header() + preamble + gcode + postamble
        # else:
        #     # fix so the preamble gets inserted in between the comments header and the actual start of GCODE
        #     g_idx = gcode.rfind('G20')
        #
        #     # if it did not find 'G20' then search for 'G21'
        #     if g_idx == -1:
        #         g_idx = gcode.rfind('G21')
        #
        #     # if it did not find 'G20' and it did not find 'G21' then there is an error and return
        #     # but only when the preprocessor is not ISEL_ICP who is allowed not to have the G20/G21 command
        #     if g_idx == -1 and isel_icp is False:
        #         self.app.inform.emit('[ERROR_NOTCL] %s' % _("G-code does not have a units code: either G20 or G21"))
        #         return
        #
        #     footer = self.app.defaults['cncjob_footer']
        #     end_gcode = self.gcode_footer() if footer is True else ''
        #     g = gcode[:g_idx] + preamble + '\n' + gcode[g_idx:] + postamble + end_gcode

        gcode = ''
        if include_header is False:
            g = preamble
            # detect if using multi-tool and make the Gcode summation correctly for each case
            if self.multitool is True:
                for tooluid_key in self.cnc_tools:
                    for key, value in self.cnc_tools[tooluid_key].items():
                        if key == 'gcode':
                            gcode += value
                            break
            else:
                gcode += self.gcode

            g = g + gcode + postamble
        else:
            # search for the GCode beginning which is usually a G20 or G21
            # fix so the preamble gets inserted in between the comments header and the actual start of GCODE
            # g_idx = gcode.rfind('G20')
            #
            # # if it did not find 'G20' then search for 'G21'
            # if g_idx == -1:
            #     g_idx = gcode.rfind('G21')
            #
            # # if it did not find 'G20' and it did not find 'G21' then there is an error and return
            # if g_idx == -1:
            #     self.app.inform.emit('[ERROR_NOTCL] %s' % _("G-code does not have a units code: either G20 or G21"))
            #     return

            # detect if using multi-tool and make the Gcode summation correctly for each case
            if self.multitool is True:
                for tooluid_key in self.cnc_tools:
                    for key, value in self.cnc_tools[tooluid_key].items():
                        if key == 'gcode':
                            gcode += value
                            break
            else:
                gcode += self.gcode

            end_gcode = self.gcode_footer() if self.app.defaults['cncjob_footer'] is True else ''

            # detect if using a HPGL preprocessor
            hpgl = False
            if self.cnc_tools:
                for key in self.cnc_tools:
                    if 'ppname_g' in self.cnc_tools[key]['data']:
                        if 'hpgl' in self.cnc_tools[key]['data']['ppname_g']:
                            hpgl = True
                            break
            elif self.exc_cnc_tools:
                for key in self.cnc_tools:
                    if 'ppname_e' in self.cnc_tools[key]['data']:
                        if 'hpgl' in self.cnc_tools[key]['data']['ppname_e']:
                            hpgl = True
                            break

            if hpgl:
                processed_gcode = ''
                pa_re = re.compile(r"^PA\s*(-?\d+\.\d*),?\s*(-?\d+\.\d*)*;?$")
                for gline in gcode.splitlines():
                    match = pa_re.search(gline)
                    if match:
                        x_int = int(float(match.group(1)))
                        y_int = int(float(match.group(2)))
                        new_line = 'PA%d,%d;\n' % (x_int, y_int)
                        processed_gcode += new_line
                    else:
                        processed_gcode += gline + '\n'

                gcode = processed_gcode
                g = self.gcode_header() + '\n' + preamble + '\n' + gcode + postamble + end_gcode
            else:
                try:
                    g_idx = gcode.index('G94')
                    g = self.gcode_header() + gcode[:g_idx + 3] + '\n\n' + preamble + '\n' + \
                        gcode[(g_idx + 3):] + postamble + end_gcode
                except ValueError:
                    self.app.inform.emit('[ERROR_NOTCL] %s' %
                                         _("G-code does not have a G94 code and we will not include the code in the "
                                           "'Prepend to GCode' text box"))
                    g = self.gcode_header() + '\n' + gcode + postamble + end_gcode

        # if toolchange custom is used, replace M6 code with the code from the Toolchange Custom Text box
        if self.ui.toolchange_cb.get_value() is True:
            # match = self.re_toolchange.search(g)
            if 'M6' in g:
                m6_code = self.parse_custom_toolchange_code(self.ui.toolchange_text.get_value())
                if m6_code is None or m6_code == '':
                    self.app.inform.emit(
                        '[ERROR_NOTCL] %s' % _("Cancelled. The Toolchange Custom code is enabled but it's empty.")
                    )
                    return 'fail'

                g = g.replace('M6', m6_code)
                self.app.inform.emit('[success] %s' % _("Toolchange G-code was replaced by a custom code."))

        lines = StringIO(g)

        # Write
        if filename is not None:
            try:
                force_windows_line_endings = self.app.defaults['cncjob_line_ending']
                if force_windows_line_endings and sys.platform != 'win32':
                    with open(filename, 'w', newline='\r\n') as f:
                        for line in lines:
                            f.write(line)
                else:
                    with open(filename, 'w') as f:
                        for line in lines:
                            f.write(line)
            except FileNotFoundError:
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("No such file or directory"))
                return
            except PermissionError:
                self.app.inform.emit(
                    '[WARNING] %s' % _("Permission denied, saving not possible.\n"
                                       "Most likely another app is holding the file open and not accessible.")
                )
                return 'fail'
        elif to_file is False:
            # Just for adding it to the recent files list.
            if self.app.defaults["global_open_style"] is False:
                self.app.file_opened.emit("cncjob", filename)
            self.app.file_saved.emit("cncjob", filename)

            self.app.inform.emit('[success] %s: %s' % (_("Saved to"), filename))
        else:
            return lines

    def on_toolchange_custom_clicked(self, signal):
        try:
            if 'toolchange_custom' not in str(self.options['ppname_e']).lower():
                if self.ui.toolchange_cb.get_value():
                    self.ui.toolchange_cb.set_value(False)
                    self.app.inform.emit('[WARNING_NOTCL] %s' %
                                         _("The used preprocessor file has to have in it's name: 'toolchange_custom'"))
        except KeyError:
            try:
                for key in self.cnc_tools:
                    ppg = self.cnc_tools[key]['data']['ppname_g']
                    if 'toolchange_custom' not in str(ppg).lower():
                        print(ppg)
                        if self.ui.toolchange_cb.get_value():
                            self.ui.toolchange_cb.set_value(False)
                            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                                 _("The used preprocessor file has to have in it's name: "
                                                   "'toolchange_custom'"))
            except KeyError:
                self.app.inform.emit('[ERROR] %s' % _("There is no preprocessor file."))

    def get_gcode(self, preamble='', postamble=''):
        # we need this to be able get_gcode separatelly for shell command export_gcode
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
        # cw = self.sender()
        # cw_index = self.ui.cnc_tools_table.indexAt(cw.pos())
        # cw_row = cw_index.row()

        kind = self.ui.cncplot_method_combo.get_value()

        self.shapes.clear(update=True)

        for tooluid_key in self.cnc_tools:
            tooldia = float('%.*f' % (self.decimals, float(self.cnc_tools[tooluid_key]['tooldia'])))
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

        if self.app.is_legacy is False:
            if self.ui.annotation_cb.get_value() and self.ui.plot_cb.get_value():
                self.text_col.enabled = True
            else:
                self.text_col.enabled = False
            self.annotation.redraw()

        try:
            if self.multitool is False:  # single tool usage
                try:
                    dia_plot = float(self.options["tooldia"])
                except ValueError:
                    # we may have a tuple with only one element and a comma
                    dia_plot = [float(el) for el in self.options["tooldia"].split(',') if el != ''][0]
                self.plot2(dia_plot, obj=self, visible=visible, kind=kind)
            else:
                # multiple tools usage
                if self.cnc_tools:
                    for tooluid_key in self.cnc_tools:
                        tooldia = float('%.*f' % (self.decimals, float(self.cnc_tools[tooluid_key]['tooldia'])))
                        gcode_parsed = self.cnc_tools[tooluid_key]['gcode_parsed']
                        self.plot2(tooldia=tooldia, obj=self, visible=visible, gcode_parsed=gcode_parsed, kind=kind)

                # TODO: until the gcode parsed will be stored on each Excellon tool this will not get executed
                if self.exc_cnc_tools:
                    for tooldia_key in self.exc_cnc_tools:
                        tooldia = float('%.*f' % (self.decimals, float(tooldia_key)))
                        # gcode_parsed = self.cnc_tools[tooldia_key]['gcode_parsed']
                        gcode_parsed = self.gcode_parsed
                        self.plot2(tooldia=tooldia, obj=self, visible=visible, gcode_parsed=gcode_parsed, kind=kind)

            self.shapes.redraw()
        except (ObjectDeleted, AttributeError):
            self.shapes.clear(update=True)
            if self.app.is_legacy is False:
                self.annotation.clear(update=True)

    def on_annotation_change(self):
        if self.app.is_legacy is False:
            if self.ui.annotation_cb.get_value():
                self.text_col.enabled = True
            else:
                self.text_col.enabled = False
            # kind = self.ui.cncplot_method_combo.get_value()
            # self.plot(kind=kind)
            self.annotation.redraw()
        else:
            kind = self.ui.cncplot_method_combo.get_value()
            self.plot(kind=kind)

    def convert_units(self, units):
        log.debug("FlatCAMObj.FlatCAMECNCjob.convert_units()")

        factor = CNCjob.convert_units(self, units)
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
                    dia_value = float('%.*f' % (self.decimals, dia_value))
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


class FlatCAMScript(FlatCAMObj):
    """
    Represents a TCL script object.
    """
    optionChanged = QtCore.pyqtSignal(str)
    ui_type = ScriptObjectUI

    def __init__(self, name):
        self.decimals = self.app.decimals

        FlatCAMApp.App.log.debug("Creating a FlatCAMScript object...")
        FlatCAMObj.__init__(self, name)

        self.kind = "script"

        self.options.update({
            "plot": True,
            "type": 'Script',
            "source_file": '',
        })

        self.units = ''

        self.ser_attrs = ['options', 'kind', 'source_file']
        self.source_file = ''
        self.script_code = ''

        self.units_found = self.app.defaults['units']

        # self.script_editor_tab = TextEditor(app=self.app, plain_text=True)
        self.script_editor_tab = TextEditor(app=self.app, plain_text=True)

    def set_ui(self, ui):
        FlatCAMObj.set_ui(self, ui)
        FlatCAMApp.App.log.debug("FlatCAMScript.set_ui()")

        assert isinstance(self.ui, ScriptObjectUI), \
            "Expected a ScriptObjectUI, got %s" % type(self.ui)

        self.units = self.app.defaults['units'].upper()
        self.units_found = self.app.defaults['units']

        # Fill form fields only on object create
        self.to_form()

        # Show/Hide Advanced Options
        if self.app.defaults["global_app_level"] == 'b':
            self.ui.level.setText(_(
                '<span style="color:green;"><b>Basic</b></span>'
            ))
        else:
            self.ui.level.setText(_(
                '<span style="color:red;"><b>Advanced</b></span>'
            ))

        # tab_here = False
        # # try to not add too many times a tab that it is already installed
        # for idx in range(self.app.ui.plot_tab_area.count()):
        #     if self.app.ui.plot_tab_area.widget(idx).objectName() == self.options['name']:
        #         tab_here = True
        #         break
        #
        # # add the tab if it is not already added
        # if tab_here is False:
        #     self.app.ui.plot_tab_area.addTab(self.script_editor_tab, '%s' % _("Script Editor"))
        #     self.script_editor_tab.setObjectName(self.options['name'])

        self.app.ui.plot_tab_area.addTab(self.script_editor_tab, '%s' % _("Script Editor"))
        self.script_editor_tab.setObjectName(self.options['name'])

        # first clear previous text in text editor (if any)
        # self.script_editor_tab.code_editor.clear()
        # self.script_editor_tab.code_editor.setReadOnly(False)

        self.ui.autocomplete_cb.set_value(self.app.defaults['script_autocompleter'])
        self.on_autocomplete_changed(state=self.app.defaults['script_autocompleter'])

        self.script_editor_tab.buttonRun.show()

        # Switch plot_area to CNCJob tab
        self.app.ui.plot_tab_area.setCurrentWidget(self.script_editor_tab)

        flt = "FlatCAM Scripts (*.FlatScript);;All Files (*.*)"
        self.script_editor_tab.buttonOpen.clicked.disconnect()
        self.script_editor_tab.buttonOpen.clicked.connect(lambda: self.script_editor_tab.handleOpen(filt=flt))
        self.script_editor_tab.buttonSave.clicked.disconnect()
        self.script_editor_tab.buttonSave.clicked.connect(lambda: self.script_editor_tab.handleSaveGCode(filt=flt))

        self.script_editor_tab.buttonRun.clicked.connect(self.handle_run_code)
        self.script_editor_tab.handleTextChanged()

        self.ui.autocomplete_cb.stateChanged.connect(self.on_autocomplete_changed)

        self.ser_attrs = ['options', 'kind', 'source_file']

        # ---------------------------------------------------- #
        # ----------- LOAD THE TEXT SOURCE FILE -------------- #
        # ---------------------------------------------------- #
        self.app.proc_container.view.set_busy(_("Loading..."))
        self.script_editor_tab.t_frame.hide()

        try:
            self.script_editor_tab.code_editor.setPlainText(self.source_file)
            # for line in self.source_file.splitlines():
            #     QtWidgets.QApplication.processEvents()
            #     self.script_editor_tab.code_editor.append(line)
        except Exception as e:
            log.debug("FlatCAMScript.set_ui() --> %s" % str(e))

        self.script_editor_tab.code_editor.moveCursor(QtGui.QTextCursor.End)
        self.script_editor_tab.t_frame.show()

        self.app.proc_container.view.set_idle()
        self.build_ui()

    def build_ui(self):
        FlatCAMObj.build_ui(self)

    def handle_run_code(self):
        # trying to run a Tcl command without having the Shell open will create some warnings because the Tcl Shell
        # tries to print on a hidden widget, therefore show the dock if hidden
        if self.app.ui.shell_dock.isHidden():
            self.app.ui.shell_dock.show()

        self.script_code = deepcopy(self.script_editor_tab.code_editor.toPlainText())

        old_line = ''
        for tcl_command_line in self.script_code.splitlines():
            # do not process lines starting with '#' = comment and empty lines
            if not tcl_command_line.startswith('#') and tcl_command_line != '':
                # id FlatCAM is run in Windows then replace all the slashes with
                # the UNIX style slash that TCL understands
                if sys.platform == 'win32':
                    if "open" in tcl_command_line:
                        tcl_command_line = tcl_command_line.replace('\\', '/')

                if old_line != '':
                    new_command = old_line + tcl_command_line + '\n'
                else:
                    new_command = tcl_command_line

                # execute the actual Tcl command
                try:
                    self.app.shell.open_processing()  # Disables input box.

                    result = self.app.tcl.eval(str(new_command))
                    if result != 'None':
                        self.app.shell.append_output(result + '\n')

                    old_line = ''
                except tk.TclError:
                    old_line = old_line + tcl_command_line + '\n'
                except Exception as e:
                    log.debug("FlatCAMScript.handleRunCode() --> %s" % str(e))

        if old_line != '':
            # it means that the script finished with an error
            result = self.app.tcl.eval("set errorInfo")
            log.error("Exec command Exception: %s" % (result + '\n'))
            self.app.shell.append_error('ERROR: ' + result + '\n')

        self.app.shell.close_processing()

    def on_autocomplete_changed(self, state):
        if state:
            self.script_editor_tab.code_editor.completer_enable = True
        else:
            self.script_editor_tab.code_editor.completer_enable = False

    def to_dict(self):
        """
        Returns a representation of the object as a dictionary.
        Attributes to include are listed in ``self.ser_attrs``.

        :return: A dictionary-encoded copy of the object.
        :rtype: dict
        """
        d = {}
        for attr in self.ser_attrs:
            d[attr] = getattr(self, attr)
        return d

    def from_dict(self, d):
        """
        Sets object's attributes from a dictionary.
        Attributes to include are listed in ``self.ser_attrs``.
        This method will look only for only and all the
        attributes in ``self.ser_attrs``. They must all
        be present. Use only for deserializing saved
        objects.

        :param d: Dictionary of attributes to set in the object.
        :type d: dict
        :return: None
        """
        for attr in self.ser_attrs:
            setattr(self, attr, d[attr])


class FlatCAMDocument(FlatCAMObj):
    """
    Represents a Document object.
    """
    optionChanged = QtCore.pyqtSignal(str)
    ui_type = DocumentObjectUI

    def __init__(self, name):
        self.decimals = self.app.decimals

        FlatCAMApp.App.log.debug("Creating a Document object...")
        FlatCAMObj.__init__(self, name)

        self.kind = "document"
        self.units = ''

        self.ser_attrs = ['options', 'kind', 'source_file']
        self.source_file = ''
        self.doc_code = ''

        self.font_italic = None
        self.font_bold = None
        self.font_underline =None

        self.document_editor_tab = None

        self._read_only = False
        self.units_found = self.app.defaults['units']

    def set_ui(self, ui):
        FlatCAMObj.set_ui(self, ui)
        FlatCAMApp.App.log.debug("FlatCAMDocument.set_ui()")

        assert isinstance(self.ui, DocumentObjectUI), \
            "Expected a DocumentObjectUI, got %s" % type(self.ui)

        self.units = self.app.defaults['units'].upper()
        self.units_found = self.app.defaults['units']

        # Fill form fields only on object create
        self.to_form()

        # Show/Hide Advanced Options
        if self.app.defaults["global_app_level"] == 'b':
            self.ui.level.setText(_(
                '<span style="color:green;"><b>Basic</b></span>'
            ))
        else:
            self.ui.level.setText(_(
                '<span style="color:red;"><b>Advanced</b></span>'
            ))

        self.document_editor_tab = TextEditor(app=self.app)
        stylesheet = """
                        QTextEdit {selection-background-color:%s;
                                   selection-color:white;
                        }
                     """ % self.app.defaults["document_sel_color"]

        self.document_editor_tab.code_editor.setStyleSheet(stylesheet)

        # first clear previous text in text editor (if any)
        self.document_editor_tab.code_editor.clear()
        self.document_editor_tab.code_editor.setReadOnly(self._read_only)

        self.document_editor_tab.buttonRun.hide()

        self.ui.autocomplete_cb.set_value(self.app.defaults['document_autocompleter'])
        self.on_autocomplete_changed(state=self.app.defaults['document_autocompleter'])
        self.on_tab_size_change(val=self.app.defaults['document_tab_size'])

        flt = "FlatCAM Docs (*.FlatDoc);;All Files (*.*)"

        # ######################################################################
        # ######################## SIGNALS #####################################
        # ######################################################################
        self.document_editor_tab.buttonOpen.clicked.disconnect()
        self.document_editor_tab.buttonOpen.clicked.connect(lambda: self.document_editor_tab.handleOpen(filt=flt))
        self.document_editor_tab.buttonSave.clicked.disconnect()
        self.document_editor_tab.buttonSave.clicked.connect(lambda: self.document_editor_tab.handleSaveGCode(filt=flt))

        self.document_editor_tab.code_editor.textChanged.connect(self.on_text_changed)

        self.ui.font_type_cb.currentFontChanged.connect(self.font_family)
        self.ui.font_size_cb.activated.connect(self.font_size)
        self.ui.font_bold_tb.clicked.connect(self.on_bold_button)
        self.ui.font_italic_tb.clicked.connect(self.on_italic_button)
        self.ui.font_under_tb.clicked.connect(self.on_underline_button)

        self.ui.font_color_entry.editingFinished.connect(self.on_font_color_entry)
        self.ui.font_color_button.clicked.connect(self.on_font_color_button)
        self.ui.sel_color_entry.editingFinished.connect(self.on_selection_color_entry)
        self.ui.sel_color_button.clicked.connect(self.on_selection_color_button)

        self.ui.al_left_tb.clicked.connect(lambda: self.document_editor_tab.code_editor.setAlignment(Qt.AlignLeft))
        self.ui.al_center_tb.clicked.connect(lambda: self.document_editor_tab.code_editor.setAlignment(Qt.AlignCenter))
        self.ui.al_right_tb.clicked.connect(lambda: self.document_editor_tab.code_editor.setAlignment(Qt.AlignRight))
        self.ui.al_justify_tb.clicked.connect(
            lambda: self.document_editor_tab.code_editor.setAlignment(Qt.AlignJustify)
        )

        self.ui.autocomplete_cb.stateChanged.connect(self.on_autocomplete_changed)
        self.ui.tab_size_spinner.returnPressed.connect(self.on_tab_size_change)
        # #######################################################################

        self.ui.font_color_entry.set_value(self.app.defaults['document_font_color'])
        self.ui.font_color_button.setStyleSheet(
            "background-color:%s" % str(self.app.defaults['document_font_color']))

        self.ui.sel_color_entry.set_value(self.app.defaults['document_sel_color'])
        self.ui.sel_color_button.setStyleSheet(
            "background-color:%s" % self.app.defaults['document_sel_color'])

        self.ui.font_size_cb.setCurrentIndex(int(self.app.defaults['document_font_size']))

        self.document_editor_tab.handleTextChanged()
        self.ser_attrs = ['options', 'kind', 'source_file']

        if Qt.mightBeRichText(self.source_file):
            self.document_editor_tab.code_editor.setHtml(self.source_file)
        else:
            for line in self.source_file.splitlines():
                self.document_editor_tab.code_editor.append(line)

        self.build_ui()

    @property
    def read_only(self):
        return self._read_only

    @read_only.setter
    def read_only(self, val):
        if val:
            self._read_only = True
        else:
            self._read_only = False

    def build_ui(self):
        FlatCAMObj.build_ui(self)
        tab_here = False

        # try to not add too many times a tab that it is already installed
        for idx in range(self.app.ui.plot_tab_area.count()):
            if self.app.ui.plot_tab_area.widget(idx).objectName() == self.options['name']:
                tab_here = True
                break

        # add the tab if it is not already added
        if tab_here is False:
            self.app.ui.plot_tab_area.addTab(self.document_editor_tab, '%s' % _("Document Editor"))
            self.document_editor_tab.setObjectName(self.options['name'])

        # Switch plot_area to CNCJob tab
        self.app.ui.plot_tab_area.setCurrentWidget(self.document_editor_tab)

    def on_autocomplete_changed(self, state):
        if state:
            self.document_editor_tab.code_editor.completer_enable = True
        else:
            self.document_editor_tab.code_editor.completer_enable = False

    def on_tab_size_change(self, val=None):
        try:
            self.ui.tab_size_spinner.returnPressed.disconnect(self.on_tab_size_change)
        except TypeError:
            pass

        if val:
            self.ui.tab_size_spinner.set_value(val)

        tab_balue = int(self.ui.tab_size_spinner.get_value())
        self.document_editor_tab.code_editor.setTabStopWidth(tab_balue)
        self.app.defaults['document_tab_size'] = tab_balue

        self.ui.tab_size_spinner.returnPressed.connect(self.on_tab_size_change)

    def on_text_changed(self):
        self.source_file = self.document_editor_tab.code_editor.toHtml()
        # print(self.source_file)

    def font_family(self, font):
        # self.document_editor_tab.code_editor.selectAll()
        font.setPointSize(float(self.ui.font_size_cb.get_value()))
        self.document_editor_tab.code_editor.setCurrentFont(font)
        self.font_name = self.ui.font_type_cb.currentFont().family()

    def font_size(self):
        # self.document_editor_tab.code_editor.selectAll()
        self.document_editor_tab.code_editor.setFontPointSize(float(self.ui.font_size_cb.get_value()))

    def on_bold_button(self):
        if self.ui.font_bold_tb.isChecked():
            self.document_editor_tab.code_editor.setFontWeight(QtGui.QFont.Bold)
            self.font_bold = True
        else:
            self.document_editor_tab.code_editor.setFontWeight(QtGui.QFont.Normal)
            self.font_bold = False

    def on_italic_button(self):
        if self.ui.font_italic_tb.isChecked():
            self.document_editor_tab.code_editor.setFontItalic(True)
            self.font_italic = True
        else:
            self.document_editor_tab.code_editor.setFontItalic(False)
            self.font_italic = False

    def on_underline_button(self):
        if self.ui.font_under_tb.isChecked():
            self.document_editor_tab.code_editor.setFontUnderline(True)
            self.font_underline = True
        else:
            self.document_editor_tab.code_editor.setFontUnderline(False)
            self.font_underline = False

    # Setting font colors handlers
    def on_font_color_entry(self):
        self.app.defaults['document_font_color'] = self.ui.font_color_entry.get_value()
        self.ui.font_color_button.setStyleSheet("background-color:%s" % str(self.app.defaults['document_font_color']))

    def on_font_color_button(self):
        current_color = QtGui.QColor(self.app.defaults['document_font_color'])

        c_dialog = QtWidgets.QColorDialog()
        font_color = c_dialog.getColor(initial=current_color)

        if font_color.isValid() is False:
            return

        self.document_editor_tab.code_editor.setTextColor(font_color)
        self.ui.font_color_button.setStyleSheet("background-color:%s" % str(font_color.name()))

        new_val = str(font_color.name())
        self.ui.font_color_entry.set_value(new_val)
        self.app.defaults['document_font_color'] = new_val

    # Setting selection colors handlers
    def on_selection_color_entry(self):
        self.app.defaults['document_sel_color'] = self.ui.sel_color_entry.get_value()
        self.ui.sel_color_button.setStyleSheet("background-color:%s" % str(self.app.defaults['document_sel_color']))

    def on_selection_color_button(self):
        current_color = QtGui.QColor(self.app.defaults['document_sel_color'])

        c_dialog = QtWidgets.QColorDialog()
        sel_color = c_dialog.getColor(initial=current_color)

        if sel_color.isValid() is False:
            return

        p = QtGui.QPalette()
        p.setColor(QtGui.QPalette.Highlight, sel_color)
        p.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor('white'))

        self.document_editor_tab.code_editor.setPalette(p)

        self.ui.sel_color_button.setStyleSheet("background-color:%s" % str(sel_color.name()))

        new_val = str(sel_color.name())
        self.ui.sel_color_entry.set_value(new_val)
        self.app.defaults['document_sel_color'] = new_val

    def to_dict(self):
        """
        Returns a representation of the object as a dictionary.
        Attributes to include are listed in ``self.ser_attrs``.

        :return: A dictionary-encoded copy of the object.
        :rtype: dict
        """
        d = {}
        for attr in self.ser_attrs:
            d[attr] = getattr(self, attr)
        return d

    def from_dict(self, d):
        """
        Sets object's attributes from a dictionary.
        Attributes to include are listed in ``self.ser_attrs``.
        This method will look only for only and all the
        attributes in ``self.ser_attrs``. They must all
        be present. Use only for deserializing saved
        objects.

        :param d: Dictionary of attributes to set in the object.
        :type d: dict
        :return: None
        """
        for attr in self.ser_attrs:
            setattr(self, attr, d[attr])

# end of file
