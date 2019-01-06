############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
############################################################

from io import StringIO
from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import Qt
from copy import copy, deepcopy
import inspect  # TODO: For debugging only.
from shapely.geometry.base import JOIN_STYLE
from datetime import datetime

import FlatCAMApp
from ObjectUI import *
from FlatCAMCommon import LoudDict
from FlatCAMEditor import FlatCAMGeoEditor
from camlib import *
from VisPyVisuals import ShapeCollectionVisual
import itertools


# Interrupts plotting process if FlatCAMObj has been deleted
class ObjectDeleted(Exception):
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

        self.item = None  # Link with project view item

        self.muted_ui = False
        self.deleted = False

        self._drawing_tolerance = 0.01

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
                setattr(self, attr, d[attr])

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
        old_name = copy(self.options["name"])
        new_name = self.ui.name_entry.get_value()

        # update the SHELL auto-completer model data
        try:
            self.app.myKeywords.remove(old_name)
            self.app.myKeywords.append(new_name)
            self.app.shell._edit.set_model_data(self.app.myKeywords)
        except:
            log.debug("on_name_activate() --> Could not remove the old object name from auto-completer model list")

        self.options["name"] = self.ui.name_entry.get_value()
        self.app.inform.emit("[success]Name changed from %s to %s" % (old_name, new_name))

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
        if type(grb_final.solid_geometry) is not list:
            grb_final.solid_geometry = [grb_final.solid_geometry]

        for grb in grb_list:

            # Expand lists
            if type(grb) is list:
                FlatCAMGerber.merge(grb, grb_final)

            # If not list, just append
            else:
                grb_final.solid_geometry.append(grb.solid_geometry)

    def __init__(self, name):
        Gerber.__init__(self, steps_per_circle=self.app.defaults["gerber_circle_steps"])
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
            "ncctools": "1.0, 0.5",
            "nccoverlap": 0.4,
            "nccmargin": 1,
            "noncoppermargin": 0.0,
            "noncopperrounded": False,
            "bboxmargin": 0.0,
            "bboxrounded": False
        })

        # type of isolation: 0 = exteriors, 1 = interiors, 2 = complete isolation (both interiors and exteriors)
        self.iso_type = 2

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from predecessors.
        self.ser_attrs += ['options', 'kind']

        # assert isinstance(self.ui, GerberObjectUI)
        # self.ui.plot_cb.stateChanged.connect(self.on_plot_cb_click)
        # self.ui.solid_cb.stateChanged.connect(self.on_solid_cb_click)
        # self.ui.multicolored_cb.stateChanged.connect(self.on_multicolored_cb_click)
        # self.ui.generate_iso_button.clicked.connect(self.on_iso_button_click)
        # self.ui.generate_cutout_button.clicked.connect(self.on_generatecutout_button_click)
        # self.ui.generate_bb_button.clicked.connect(self.on_generatebb_button_click)
        # self.ui.generate_noncopper_button.clicked.connect(self.on_generatenoncopper_button_click)

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
            "bboxrounded": self.ui.bbrounded_cb
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

    def on_generatenoncopper_button_click(self, *args):
        self.app.report_usage("gerber_on_generatenoncopper_button")

        self.read_form()
        name = self.options["name"] + "_noncopper"

        def geo_init(geo_obj, app_obj):
            assert isinstance(geo_obj, FlatCAMGeometry)
            bounding_box = self.solid_geometry.envelope.buffer(self.options["noncoppermargin"])
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
            bounding_box = self.solid_geometry.envelope.buffer(self.options["bboxmargin"])
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

        if self.ui.follow_cb.get_value() == True:
            obj = self.app.collection.get_active()
            obj.follow()
            # in the end toggle the visibility of the origin object so we can see the generated Geometry
            obj.ui.plot_cb.toggle()
        else:
            self.app.report_usage("gerber_on_iso_button")
            self.read_form()
            self.isolate(iso_type=1)

    def on_iso_button_click(self, *args):

        if self.ui.follow_cb.get_value() == True:
            obj = self.app.collection.get_active()
            obj.follow()
            # in the end toggle the visibility of the origin object so we can see the generated Geometry
            obj.ui.plot_cb.toggle()
        else:
            self.app.report_usage("gerber_on_iso_button")
            self.read_form()
            self.isolate()

    def follow(self, outname=None):
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
            follow_obj.options["cnctooldia"] = self.options["isotooldia"]
            follow_obj.solid_geometry = self.solid_geometry

        # TODO: Do something if this is None. Offer changing name?
        try:
            self.app.new_object("geometry", follow_name, follow_init)
        except Exception as e:
            return "Operation failed: %s" % str(e)

    def isolate(self, iso_type=None, dia=None, passes=None, overlap=None,
                outname=None, combine=None, milling_type=None):
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
            dia = self.options["isotooldia"]
        if passes is None:
            passes = int(self.options["isopasses"])
        if overlap is None:
            overlap = self.options["isooverlap"]
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

        def generate_envelope(offset, invert, envelope_iso_type=2):
            # isolation_geometry produces an envelope that is going on the left of the geometry
            # (the copper features). To leave the least amount of burrs on the features
            # the tool needs to travel on the right side of the features (this is called conventional milling)
            # the first pass is the one cutting all of the features, so it needs to be reversed
            # the other passes overlap preceding ones and cut the left over copper. It is better for them
            # to cut on the right side of the left over copper i.e on the left side of the features.
            try:
                geom = self.isolation_geometry(offset, iso_type=envelope_iso_type)
            except Exception as e:
                log.debug(str(e))

            if invert:
                try:
                    if type(geom) is MultiPolygon:
                        pl = []
                        for p in geom:
                            pl.append(Polygon(p.exterior.coords[::-1], p.interiors))
                        geom = MultiPolygon(pl)
                    elif type(geom) is Polygon:
                        geom = Polygon(geom.exterior.coords[::-1], geom.interiors)
                except Exception as e:
                    s = str("Unexpected Geometry")
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
                geo_obj.options["cnctooldia"] = self.options["isotooldia"]
                geo_obj.solid_geometry = []
                for i in range(passes):
                    offset = (((2 * i + 1) / 2.0) * dia) - (i * overlap * dia)

                    # if milling type is climb then the move is counter-clockwise around features
                    if milling_type == 'cl':
                        # geom = generate_envelope (offset, i == 0)
                        geom = generate_envelope(offset, 1, envelope_iso_type=self.iso_type)
                    else:
                        geom = generate_envelope(offset, 0, envelope_iso_type=self.iso_type)
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
                        app_obj.inform.emit("[success]Isolation geometry created: %s" % geo_obj.options["name"])
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
                    geo_obj.options["cnctooldia"] = self.options["isotooldia"]

                    # if milling type is climb then the move is counter-clockwise around features
                    if milling_type == 'cl':
                        # geo_obj.solid_geometry = generate_envelope(offset, i == 0)
                        geo_obj.solid_geometry = generate_envelope(offset, 1, envelope_iso_type=self.iso_type)
                    else:
                        geo_obj.solid_geometry = generate_envelope(offset, 0, envelope_iso_type=self.iso_type)

                    # detect if solid_geometry is empty and this require list flattening which is "heavy"
                    # or just looking in the lists (they are one level depth) and if any is not empty
                    # proceed with object creation, if there are empty and the number of them is the length
                    # of the list then we have an empty solid_geometry which should raise a Custom Exception
                    empty_cnt = 0
                    if not isinstance(geo_obj.solid_geometry, list):
                        geo_obj.solid_geometry = [geo_obj.solid_geometry]

                    for g in geo_obj.solid_geometry:
                        if g:
                            app_obj.inform.emit("[success]Isolation geometry created: %s" % geo_obj.options["name"])
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

        self.options['isotooldia'] *= factor
        self.options['cutoutmargin'] *= factor
        self.options['cutoutgapsize'] *= factor
        self.options['noncoppermargin'] *= factor
        self.options['bboxmargin'] *= factor

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
                    else:
                        for el in g:
                            self.add_shape(shape=el, color=random_color() if self.options['multicolored'] else 'black',
                                           visible=self.options['plot'])
            self.shapes.redraw()
        except (ObjectDeleted, AttributeError):
            self.shapes.clear(update=True)

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
        Excellon.__init__(self, geo_steps_per_circle=self.app.defaults["geometry_circle_steps"])
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
            "optimization_type": "R",
            "gcode_type": "drills"
        })

        # TODO: Document this.
        self.tool_cbs = {}

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from predecessors.
        self.ser_attrs += ['options', 'kind']

        # variable to store the total amount of drills per job
        self.tot_drill_cnt = 0
        self.tool_row = 0

        # variable to store the total amount of slots per job
        self.tot_slot_cnt = 0
        self.tool_row_slots = 0


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

        try:
            flattened_list = list(itertools.chain(*exc_list))
        except TypeError:
            flattened_list = exc_list

        # this dict will hold the unique tool diameters found in the exc_list objects as the dict keys and the dict
        # values will be list of Shapely Points
        custom_dict = {}

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

                if exc_tool_dia not in custom_dict:
                    custom_dict[exc_tool_dia] = [drill['point']]
                else:
                    custom_dict[exc_tool_dia].append(drill['point'])

                # add the zeros and units to the exc_final object
            exc_final.zeros = exc.zeros
            exc_final.units = exc.units

        # variable to make tool_name for the tools
        current_tool = 0

        # Here we add data to the exc_final object
        # the tools diameter are now the keys in the drill_dia dict and the values are the Shapely Points
        for tool_dia in custom_dict:
            # we create a tool name for each key in the drill_dia dict (the key is a unique drill diameter)
            current_tool += 1

            tool_name = str(current_tool)
            spec = {"C": float(tool_dia)}
            exc_final.tools[tool_name] = spec

            # rebuild the drills list of dict's that belong to the exc_final object
            for point in custom_dict[tool_dia]:
                exc_final.drills.append(
                    {
                        "point": point,
                        "tool": str(current_tool)
                    }
                )

        # create the geometry for the exc_final object
        exc_final.create_geometry()

    def build_ui(self):
        FlatCAMObj.build_ui(self)

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

            self.ui.tools_table.setItem(self.tool_row, 1, dia)  # Diameter
            self.ui.tools_table.setItem(self.tool_row, 2, drill_count)  # Number of drills per tool
            self.ui.tools_table.setItem(self.tool_row, 3, slot_count)  # Number of drills per tool
            self.tool_row += 1

        # add a last row with the Total number of drills
        empty = QtWidgets.QTableWidgetItem('')
        empty.setFlags(~QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)

        label_tot_drill_count = QtWidgets.QTableWidgetItem('Total Drills')
        tot_drill_count = QtWidgets.QTableWidgetItem('%d' % self.tot_drill_cnt)
        label_tot_drill_count.setFlags(QtCore.Qt.ItemIsEnabled)
        tot_drill_count.setFlags(QtCore.Qt.ItemIsEnabled)

        self.ui.tools_table.setItem(self.tool_row, 0, empty)
        self.ui.tools_table.setItem(self.tool_row, 1, label_tot_drill_count)
        self.ui.tools_table.setItem(self.tool_row, 2, tot_drill_count)  # Total number of drills

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

        label_tot_slot_count = QtWidgets.QTableWidgetItem('Total Slots')
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
        self.ui.tools_table.sortItems(1)
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
        horizontal_header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        horizontal_header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        # horizontal_header.setStretchLastSection(True)

        self.ui.tools_table.setSortingEnabled(True)

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
            "gcode_type": self.ui.excellon_gcode_type_radio
        })

        for name in list(self.app.postprocessors.keys()):
            self.ui.pp_excellon_name_cb.addItem(name)

        # Fill form fields
        self.to_form()

        assert isinstance(self.ui, ExcellonObjectUI), \
            "Expected a ExcellonObjectUI, got %s" % type(self.ui)
        self.ui.plot_cb.stateChanged.connect(self.on_plot_cb_click)
        self.ui.solid_cb.stateChanged.connect(self.on_solid_cb_click)
        self.ui.generate_cnc_button.clicked.connect(self.on_create_cncjob_button_click)
        self.ui.generate_milling_button.clicked.connect(self.on_generate_milling_button_click)
        self.ui.generate_milling_slots_button.clicked.connect(self.on_generate_milling_slots_button_click)

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
            table_tools_items.append([self.ui.tools_table.item(x.row(), column).text()
                                      for column in range(0, self.ui.tools_table.columnCount())])
        for item in table_tools_items:
            item[0] = str(item[0])
        return table_tools_items

    def export_excellon(self):
        """
        Returns two values, first is a boolean , if 1 then the file has slots and second contain the Excellon code
        :return: has_slots and Excellon_code
        """

        excellon_code = ''
        units = self.app.general_options_form.general_group.units_radio.get_value().upper()

        # store here if the file has slots, return 1 if any slots, 0 if only drills
        has_slots = 0

        # drills processing
        try:
            for tool in self.tools:
                if int(tool) < 10:
                    excellon_code += 'T0' + str(tool) + '\n'
                else:
                    excellon_code += 'T' + str(tool) + '\n'

                for drill in self.drills:
                    if tool == drill['tool']:
                        if units == 'MM':
                            excellon_code += 'X' + '%.3f' % drill['point'].x + 'Y' + '%.3f' % drill['point'].y + '\n'
                        else:
                            excellon_code += 'X' + '%.4f' % drill['point'].x + 'Y' + '%.4f' % drill['point'].y + '\n'
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
                        if tool == slot['tool']:
                            if units == 'MM':
                                excellon_code += 'G00' + 'X' + '%.3f' % slot['start'].x + 'Y' + \
                                                 '%.3f' % slot['start'].y + '\n'
                                excellon_code += 'M15\n'
                                excellon_code += 'G01' + 'X' + '%.3f' % slot['stop'].x + 'Y' + \
                                                 '%.3f' % slot['stop'].y + '\n'
                                excellon_code += 'M16\n'
                            else:
                                excellon_code += 'G00' + 'X' + '%.4f' % slot['start'].x + 'Y' + \
                                                 '%.4f' % slot['start'].y + '\n'
                                excellon_code += 'M15\n'
                                excellon_code += 'G01' + 'X' + '%.4f' % slot['stop'].x + 'Y' + \
                                                 '%.4f' % slot['stop'].y + '\n'
                                excellon_code += 'M16\n'
        except Exception as e:
            log.debug(str(e))

        return has_slots, excellon_code

    def export_excellon_altium(self):
        """
        Returns two values, first is a boolean , if 1 then the file has slots and second contain the Excellon code
        :return: has_slots and Excellon_code
        """

        excellon_code = ''
        units = self.app.general_options_form.general_group.units_radio.get_value().upper()

        # store here if the file has slots, return 1 if any slots, 0 if only drills
        has_slots = 0

        # drills processing
        try:
            for tool in self.tools:
                if int(tool) < 10:
                    excellon_code += 'T0' + str(tool) + '\n'
                else:
                    excellon_code += 'T' + str(tool) + '\n'

                for drill in self.drills:
                    if tool == drill['tool']:
                        drill_x = drill['point'].x
                        drill_y = drill['point'].y
                        if units == 'MM':
                            drill_x /= 25.4
                            drill_y /= 25.4
                        exc_x_formatted = ('%.4f' % drill_x).replace('.', '')
                        if drill_x < 10:
                            exc_x_formatted = '0' + exc_x_formatted

                        exc_y_formatted = ('%.4f' % drill_y).replace('.', '')
                        if drill_y < 10:
                            exc_y_formatted = '0' + exc_y_formatted

                        excellon_code += 'X' + exc_x_formatted + 'Y' + exc_y_formatted + '\n'
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
                        if tool == slot['tool']:
                            start_slot_x = slot['start'].x
                            start_slot_y = slot['start'].y
                            stop_slot_x = slot['stop'].x
                            stop_slot_y = slot['stop'].y
                            if units == 'MM':
                                start_slot_x /= 25.4
                                start_slot_y /= 25.4
                                stop_slot_x /= 25.4
                                stop_slot_y /= 25.4

                            start_slot_x_formatted = ('%.4f' % start_slot_x).replace('.', '')
                            if start_slot_x < 10:
                                start_slot_x_formatted = '0' + start_slot_x_formatted

                            start_slot_y_formatted = ('%.4f' % start_slot_y).replace('.', '')
                            if start_slot_y < 10:
                                start_slot_y_formatted = '0' + start_slot_y_formatted

                            stop_slot_x_formatted = ('%.4f' % stop_slot_x).replace('.', '')
                            if stop_slot_x < 10:
                                stop_slot_x_formatted = '0' + stop_slot_x_formatted

                            stop_slot_y_formatted = ('%.4f' % stop_slot_y).replace('.', '')
                            if stop_slot_y < 10:
                                stop_slot_y_formatted = '0' + stop_slot_y_formatted

                            excellon_code += 'G00' + 'X' + start_slot_x_formatted + 'Y' + \
                                             start_slot_y_formatted + '\n'
                            excellon_code += 'M15\n'
                            excellon_code += 'G01' + 'X' + stop_slot_x_formatted + 'Y' + \
                                             stop_slot_y_formatted + '\n'
                            excellon_code += 'M16\n'
        except Exception as e:
            log.debug(str(e))

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
            tooldia = self.options["tooldia"]

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
            self.app.inform.emit("[error_notcl]Please select one or more tools from the list and try again.")
            return False, "Error: No tools."

        for tool in tools:
            if tooldia > self.tools[tool]["C"]:
                self.app.inform.emit("[error_notcl] Milling tool for DRILLS is larger than hole size. Cancelled.")
                return False, "Error: Milling tool is larger than hole."

        def geo_init(geo_obj, app_obj):
            assert isinstance(geo_obj, FlatCAMGeometry), \
                "Initializer expected a FlatCAMGeometry, got %s" % type(geo_obj)
            app_obj.progress.emit(20)

            ### Add properties to the object

            # get the tool_table items in a list of row items
            tool_table_items = self.get_selected_tools_table_items()
            # insert an information only element in the front
            tool_table_items.insert(0, ["Tool_nr", "Diameter", "Drills_Nr", "Slots_Nr"])

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
            tooldia = self.options["slot_tooldia"]

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
            self.app.inform.emit("[error_notcl]Please select one or more tools from the list and try again.")
            return False, "Error: No tools."

        for tool in tools:
            if tooldia > self.tools[tool]["C"]:
                self.app.inform.emit("[error_notcl] Milling tool for SLOTS is larger than hole size. Cancelled.")
                return False, "Error: Milling tool is larger than hole."

        def geo_init(geo_obj, app_obj):
            assert isinstance(geo_obj, FlatCAMGeometry), \
                "Initializer expected a FlatCAMGeometry, got %s" % type(geo_obj)
            app_obj.progress.emit(20)

            ### Add properties to the object

            # get the tool_table items in a list of row items
            tool_table_items = self.get_selected_tools_table_items()
            # insert an information only element in the front
            tool_table_items.insert(0, ["Tool_nr", "Diameter", "Drills_Nr", "Slots_Nr"])

            geo_obj.options['Tools_in_use'] = tool_table_items
            geo_obj.options['type'] = 'Excellon Geometry'

            geo_obj.solid_geometry = []

            # in case that the tool used has the same diameter with the hole, and since the maximum resolution
            # for FlatCAM is 6 decimals,
            # we add a tenth of the minimum value, meaning 0.0000001, which from our point of view is "almost zero"
            for slot in self.slots:
                if slot['tool'] in tools:
                    buffer_value = self.tools[slot['tool']]["C"] / 2 - tooldia / 2
                    if buffer_value == 0:
                        start = slot['start']
                        stop = slot['stop']

                        lines_string = LineString([start, stop])
                        poly = lines_string.buffer(0.0000001, self.geo_steps_per_circle).exterior
                        geo_obj.solid_geometry.append(poly)
                    else:
                        start = slot['start']
                        stop = slot['stop']

                        lines_string = LineString([start, stop])
                        poly = lines_string.buffer(buffer_value, self.geo_steps_per_circle).exterior
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

    def on_create_cncjob_button_click(self, *args):
        self.app.report_usage("excellon_on_create_cncjob_button")
        self.read_form()

        # Get the tools from the list
        tools = self.get_selected_tools_list()

        if len(tools) == 0:
            self.app.inform.emit("[error_notcl]Please select one or more tools from the list and try again.")
            return

        job_name = self.options["name"] + "_cnc"
        pp_excellon_name = self.options["ppname_e"]

        # Object initialization function for app.new_object()
        def job_init(job_obj, app_obj):
            assert isinstance(job_obj, FlatCAMCNCjob), \
                "Initializer expected a FlatCAMCNCjob, got %s" % type(job_obj)

            # get the tool_table items in a list of row items
            tool_table_items = self.get_selected_tools_table_items()
            # insert an information only element in the front
            tool_table_items.insert(0, ["Tool_nr", "Diameter", "Drills_Nr", "Slots_Nr"])

            ### Add properties to the object

            job_obj.options['Tools_in_use'] = tool_table_items
            job_obj.options['type'] = 'Excellon'

            app_obj.progress.emit(20)
            job_obj.z_cut = self.options["drillz"]
            job_obj.z_move = self.options["travelz"]
            job_obj.feedrate = self.options["feedrate"]
            job_obj.feedrate_rapid = self.options["feedrate_rapid"]
            job_obj.spindlespeed = self.options["spindlespeed"]
            job_obj.dwell = self.options["dwell"]
            job_obj.dwelltime = self.options["dwelltime"]
            job_obj.pp_excellon_name = pp_excellon_name
            job_obj.toolchange_xy = "excellon"
            job_obj.coords_decimals = int(self.app.defaults["cncjob_coords_decimals"])
            job_obj.fr_decimals = int(self.app.defaults["cncjob_fr_decimals"])

            # There could be more than one drill size...
            # job_obj.tooldia =   # TODO: duplicate variable!
            # job_obj.options["tooldia"] =

            tools_csv = ','.join(tools)
            job_obj.generate_from_excellon_by_tool(self, tools_csv,
                                                   drillz=self.options['drillz'],
                                                   toolchange=self.options["toolchange"],
                                                   toolchangez=self.options["toolchangez"],
                                                   toolchangexy=self.options["toolchangexy"],
                                                   startz=self.options["startz"],
                                                   endz=self.options["endz"],
                                                   excellon_optimization_type=self.options["optimization_type"])

            app_obj.progress.emit(50)
            job_obj.gcode_parse()

            app_obj.progress.emit(60)
            job_obj.create_geometry()

            app_obj.progress.emit(80)

        # To be run in separate thread
        def job_thread(app_obj):
            with self.app.proc_container.new("Generating CNC Code"):
                app_obj.new_object("cncjob", job_name, job_init)
                app_obj.progress.emit(100)

        # Create promise for the new name.
        self.app.collection.promise(job_name)

        # Send to worker
        # self.app.worker.add_task(job_thread, [self.app])
        self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})

    def on_plot_cb_click(self, *args):
        if self.muted_ui:
            return
        self.read_form_item('plot')

    def on_solid_cb_click(self, *args):
        if self.muted_ui:
            return
        self.read_form_item('solid')
        self.plot()

    def convert_units(self, units):
        factor = Excellon.convert_units(self, units)

        self.options['drillz'] *= factor
        self.options['travelz'] *= factor
        self.options['feedrate'] *= factor
        self.options['feedrate_rapid'] *= factor
        self.options['toolchangez'] *= factor

        coords_xy = [float(eval(coord)) for coord in self.app.defaults["excellon_toolchangexy"].split(",")]
        coords_xy[0] *= factor
        coords_xy[1] *= factor
        self.options['toolchangexy'] = "%f, %f" % (coords_xy[0], coords_xy[1])

        if self.options['startz'] is not None:
            self.options['startz'] *= factor
        self.options['endz'] *= factor

    def plot(self):

        # Does all the required setup and returns False
        # if the 'ptint' option is set to False.
        if not FlatCAMObj.plot(self):
            return

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

                # add and merge tools
                for tool_uid in geo.tools:
                    max_uid += 1
                    geo_final.tools[max_uid] = dict(geo.tools[tool_uid])

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
        Geometry.__init__(self, geo_steps_per_circle=self.app.defaults["geometry_circle_steps"])

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

        self.offset_item_options = ["Path", "In", "Out", "Custom"]
        self.type_item_options = ["Iso", "Rough", "Finish"]
        self.tool_type_item_options = ["C1", "C2", "C3", "C4", "B", "V"]

        # flag to store if the V-Shape tool is selected in self.ui.geo_tools_table
        self.v_tool_type = None

        self.multigeo = False

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
                    'tooldia': self.options["cnctooldia"],
                    'offset': 'Path',
                    'offset_value': 0.0,
                    'type': 'Rough',
                    'tool_type': 'C1',
                    'data': self.default_data,
                    'solid_geometry': []
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
                val =  dict(self.tools[tooluid_key])
                new_key = deepcopy(int(tooluid_key))
                temp_tools[new_key] = val

            self.tools.clear()
            self.tools = dict(temp_tools)

        self.ui.tool_offset_entry.hide()
        self.ui.tool_offset_lbl.hide()

        assert isinstance(self.ui, GeometryObjectUI), \
            "Expected a GeometryObjectUI, got %s" % type(self.ui)

        self.ui.geo_tools_table.setupContextMenu()
        self.ui.geo_tools_table.addContextMenu(
            "Copy", self.on_tool_copy, icon=QtGui.QIcon("share/copy16.png"))
        self.ui.geo_tools_table.addContextMenu(
            "Delete", lambda: self.on_tool_delete(all=None), icon=QtGui.QIcon("share/delete32.png"))

        self.ui.plot_cb.stateChanged.connect(self.on_plot_cb_click)
        self.ui.generate_cnc_button.clicked.connect(self.on_generatecnc_button_click)
        self.ui.paint_tool_button.clicked.connect(self.app.paint_tool.run)

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
                    tooluid_value['offset_value'] = self.ui.tool_offset_entry.get_value()

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
                        isinstance(self.ui.grid3.itemAt(i), IntEntry) or \
                        isinstance(self.ui.grid3.itemAt(i), FCEntry):
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

        if dia is not None:
            tooldia = dia
        else:
            tooldia = self.ui.addtool_entry.get_value()
            if tooldia is None:
                self.build_ui()
                self.app.inform.emit("[error_notcl] Please enter the desired tool diameter in Float format.")
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
                    'offset': 'Path',
                    'offset_value': 0.0,
                    'type': 'Rough',
                    'tool_type': 'C1',
                    'data': dict(self.default_data),
                    'solid_geometry': []
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

            self.tools.update({
                self.tooluid: {
                    'tooldia': tooldia,
                    'offset': last_offset,
                    'offset_value': last_offset_value,
                    'type': last_type,
                    'tool_type': last_tool_type,
                    'data': dict(last_data),
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

        self.app.inform.emit("[success] Tool added in Tool Table.")
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
                        self.tools[int(max_uid)] = dict(self.tools[tooluid_copy])
                    except AttributeError:
                        self.app.inform.emit("[warning_notcl]Failed. Select a tool to copy.")
                        self.build_ui()
                        return
                    except Exception as e:
                        log.debug("on_tool_copy() --> " + str(e))
                # deselect the table
                # self.ui.geo_tools_table.clearSelection()
            else:
                self.app.inform.emit("[warning_notcl]Failed. Select a tool to copy.")
                self.build_ui()
                return
        else:
            # we copy all tools in geo_tools_table
            try:
                temp_tools = dict(self.tools)
                max_uid += 1
                for tooluid in temp_tools:
                    self.tools[int(max_uid)] = dict(temp_tools[tooluid])
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
        self.app.inform.emit("[success] Tool was copied in Tool Table.")

    def on_tool_edit(self, current_item):

        self.ui_disconnect()

        current_row = current_item.row()
        tool_dia = float('%.4f' % float(self.ui.geo_tools_table.item(current_row, 1).text()))
        tooluid = int(self.ui.geo_tools_table.item(current_row, 5).text())

        self.tools[tooluid]['tooldia'] = tool_dia

        try:
            self.ser_attrs.remove('tools')
            self.ser_attrs.append('tools')
        except:
            pass

        self.app.inform.emit("[success] Tool was edited in Tool Table.")
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

                        temp_tools = dict(self.tools)
                        for tooluid_key in self.tools:
                            if int(tooluid_key) == tooluid_del:
                                temp_tools.pop(tooluid_del, None)
                        self.tools = dict(temp_tools)
                        temp_tools.clear()
                    except AttributeError:
                        self.app.inform.emit("[warning_notcl]Failed. Select a tool to delete.")
                        self.build_ui()
                        return
                    except Exception as e:
                        log.debug("on_tool_delete() --> " + str(e))
                # deselect the table
                # self.ui.geo_tools_table.clearSelection()
            else:
                self.app.inform.emit("[warning_notcl]Failed. Select a tool to delete.")
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
        self.app.inform.emit("[success] Tool was deleted in Tool Table.")

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
        vdia = float(self.ui.tipdia_entry.get_value())
        half_vangle = float(self.ui.tipangle_entry.get_value()) / 2

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
                        tooluid_value['type'] = 'Iso'
                        idx = self.ui.geo_tools_table.cellWidget(cw_row, 3).findText('Iso')
                        self.ui.geo_tools_table.cellWidget(cw_row, 3).setCurrentIndex(idx)
                    else:
                        tooluid_value['type'] = cb_txt
                elif cw_col == 4:
                    tooluid_value['tool_type'] = cb_txt

                    # if the tool_type selected is V-Shape then autoselect the toolpath type as Iso
                    if cb_txt == 'V':
                        idx = self.ui.geo_tools_table.cellWidget(cw_row, 3).findText('Iso')
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

        offset_value_item = self.ui.tool_offset_entry.get_value()

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
                        temp_dia[key] = dict(temp_data)
                        temp_data.clear()

                    if key == 'solid_geometry':
                        temp_dia[key] = deepcopy(self.tools[tooluid_key]['solid_geometry'])

                    temp_tools[tooluid_key] = dict(temp_dia)

            else:
                temp_tools[tooluid_key] = dict(tooluid_value)

        self.tools.clear()
        self.tools = dict(temp_tools)
        temp_tools.clear()
        self.ui_connect()

    def select_tools_table_row(self, row, clearsel=None):
        if clearsel:
            self.ui.geo_tools_table.clearSelection()

        if self.ui.geo_tools_table.rowCount() > 0:
            # self.ui.geo_tools_table.item(row, 0).setSelected(True)
            self.ui.geo_tools_table.setCurrentItem(self.ui.geo_tools_table.item(row, 0))

    def export_dxf(self):
        units = self.app.general_options_form.general_group.units_radio.get_value().upper()
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

    def on_generatecnc_button_click(self, *args):

        self.app.report_usage("geometry_on_generatecnc_button")
        self.read_form()

        # test to see if we have tools available in the tool table
        if self.ui.geo_tools_table.selectedItems():
            for x in self.ui.geo_tools_table.selectedItems():
                tooldia = float(self.ui.geo_tools_table.item(x.row(), 1).text())
                tooluid = int(self.ui.geo_tools_table.item(x.row(), 5).text())

                for tooluid_key, tooluid_value in self.tools.items():
                    if int(tooluid_key) == tooluid:
                        self.sel_tools.update({
                            tooluid: dict(tooluid_value)
                        })
            self.mtool_gen_cncjob()

            self.ui.geo_tools_table.clearSelection()
        else:
            self.app.inform.emit("[error_notcl] Failed. No tool selected in the tool table ...")

    def mtool_gen_cncjob(self, use_thread=True):
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

                        datadict = dict(diadict_value)
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
                    offset_value = self.ui.tool_offset_entry.get_value()
                    if offset_value:
                        tool_offset = float(offset_value)
                    else:
                        self.app.inform.emit(
                            "[warning] Tool Offset is selected in Tool Table but no value is provided.\n"
                            "Add a Tool Offset or change the Offset Type."
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

                dia_cnc_dict['gcode'] = job_obj.generate_from_geometry_2(
                    self, tooldia=tooldia_val, offset=tool_offset, tolerance=0.0005,
                    z_cut=z_cut, z_move=z_move,
                    feedrate=feedrate, feedrate_z=feedrate_z, feedrate_rapid=feedrate_rapid,
                    spindlespeed=spindlespeed, dwell=dwell, dwelltime=dwelltime,
                    multidepth=multidepth, depthpercut=depthpercut,
                    extracut=extracut, startz=startz, endz=endz,
                    toolchange=toolchange, toolchangez=toolchangez, toolchangexy=toolchangexy,
                    pp_geometry_name=pp_geometry_name,
                    tool_no=tool_cnt)

                app_obj.progress.emit(50)
                # tell gcode_parse from which point to start drawing the lines depending on what kind of
                # object is the source of gcode
                job_obj.toolchange_xy = "geometry"

                dia_cnc_dict['gcode_parsed'] = job_obj.gcode_parse()

                # TODO this serve for bounding box creation only; should be optimized
                dia_cnc_dict['solid_geometry'] = cascaded_union([geo['geom'] for geo in dia_cnc_dict['gcode_parsed']])

                app_obj.progress.emit(80)

                job_obj.cnc_tools.update({
                    tooluid_key: dict(dia_cnc_dict)
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

                        datadict = dict(diadict_value)
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
                    offset_value = self.ui.tool_offset_entry.get_value()
                    if offset_value:
                        tool_offset = float(offset_value)
                    else:
                        self.app.inform.emit(
                            "[warning] Tool Offset is selected in Tool Table but no value is provided.\n"
                            "Add a Tool Offset or change the Offset Type."
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
                dia_cnc_dict['gcode'] = job_obj.generate_from_multitool_geometry(
                    tool_solid_geometry, tooldia=tooldia_val, offset=tool_offset,
                    tolerance=0.0005, z_cut=z_cut, z_move=z_move,
                    feedrate=feedrate, feedrate_z=feedrate_z, feedrate_rapid=feedrate_rapid,
                    spindlespeed=spindlespeed, dwell=dwell, dwelltime=dwelltime,
                    multidepth=multidepth, depthpercut=depthpercut,
                    extracut=extracut, startz=startz, endz=endz,
                    toolchange=toolchange, toolchangez=toolchangez, toolchangexy=toolchangexy,
                    pp_geometry_name=pp_geometry_name,
                    tool_no=tool_cnt)

                dia_cnc_dict['gcode_parsed'] = job_obj.gcode_parse()

                # TODO this serve for bounding box creation only; should be optimized
                dia_cnc_dict['solid_geometry'] = cascaded_union([geo['geom'] for geo in dia_cnc_dict['gcode_parsed']])

                # tell gcode_parse from which point to start drawing the lines depending on what kind of
                # object is the source of gcode
                job_obj.toolchange_xy = "geometry"

                app_obj.progress.emit(80)

                job_obj.cnc_tools.update({
                    tooluid_key: dict(dia_cnc_dict)
                })
                dia_cnc_dict.clear()

        if use_thread:
            # To be run in separate thread
            # The idea is that if there is a solid_geometry in the file "root" then most likely thare are no
            # separate solid_geometry in the self.tools dictionary
            def job_thread(app_obj):
                if self.solid_geometry:
                    with self.app.proc_container.new("Generating CNC Code"):
                        app_obj.new_object("cncjob", outname, job_init_single_geometry)
                        app_obj.inform.emit("[success]CNCjob created: %s" % outname)
                        app_obj.progress.emit(100)
                else:
                    with self.app.proc_container.new("Generating CNC Code"):
                        app_obj.new_object("cncjob", outname, job_init_multi_geometry)
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
        tooldia = tooldia if tooldia else self.options["cnctooldia"]
        outname = outname if outname is not None else self.options["name"]

        z_cut = z_cut if z_cut is not None else self.options["cutz"]
        z_move = z_move if z_move is not None else self.options["travelz"]

        feedrate = feedrate if feedrate is not None else self.options["feedrate"]
        feedrate_z = feedrate_z if feedrate_z is not None else self.options["feedrate_z"]
        feedrate_rapid = feedrate_rapid if feedrate_rapid is not None else self.options["feedrate_rapid"]

        multidepth = multidepth if multidepth is not None else self.options["multidepth"]
        depthperpass = depthperpass if depthperpass is not None else self.options["depthperpass"]

        extracut = extracut if extracut is not None else self.options["extracut"]
        startz = startz if startz is not None else self.options["startz"]
        endz = endz if endz is not None else self.options["endz"]

        toolchangez = toolchangez if toolchangez else self.options["toolchangez"]
        toolchangexy = toolchangexy if toolchangexy else self.options["toolchangexy"]
        toolchange = toolchange if toolchange else self.options["toolchange"]

        offset = offset if offset else 0.0

        # int or None.
        spindlespeed = spindlespeed if spindlespeed else self.options['spindlespeed']
        dwell = dwell if dwell else self.options["dwell"]
        dwelltime = dwelltime if dwelltime else self.options["dwelltime"]

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
            job_obj.toolchange_xy = "geometry"
            job_obj.gcode_parse()

            app_obj.progress.emit(80)

        if use_thread:
            # To be run in separate thread
            def job_thread(app_obj):
                with self.app.proc_container.new("Generating CNC Code"):
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

        if yfactor is None:
            yfactor = xfactor

        if point is None:
            px = 0
            py = 0
        else:
            px, py = point

        if type(self.solid_geometry) == list:
            geo_list =  self.flatten(self.solid_geometry)
            self.solid_geometry = []
            # for g in geo_list:
            #     self.solid_geometry.append(affinity.scale(g, xfactor, yfactor, origin=(px, py)))
            self.solid_geometry = [affinity.scale(g, xfactor, yfactor, origin=(px, py))
                                   for g in geo_list]
        else:
            self.solid_geometry = affinity.scale(self.solid_geometry, xfactor, yfactor,
                                                 origin=(px, py))

    def offset(self, vect):
        """
        Offsets all geometry by a given vector/

        :param vect: (x, y) vector by which to offset the object's geometry.
        :type vect: tuple
        :return: None
        :rtype: None
        """

        dx, dy = vect

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

    def convert_units(self, units):
        self.ui_disconnect()

        factor = Geometry.convert_units(self, units)

        self.options['cutz'] *= factor
        self.options['depthperpass'] *= factor
        self.options['travelz'] *= factor
        self.options['feedrate'] *= factor
        self.options['feedrate_z'] *= factor
        self.options['feedrate_rapid'] *= factor
        self.options['endz'] *= factor
        # self.options['cnctooldia'] *= factor
        self.options['painttooldia'] *= factor
        self.options['paintmargin'] *= factor
        self.options['paintoverlap'] *= factor

        self.options["toolchangez"] *= factor

        coords_xy = [float(eval(coord)) for coord in self.app.defaults["geometry_toolchangexy"].split(",")]
        coords_xy[0] *= factor
        coords_xy[1] *= factor
        self.options['toolchangexy'] = "%f, %f" % (coords_xy[0], coords_xy[1])

        if self.options['startz'] is not None:
            self.options['startz'] *= factor

        param_list = ['cutz', 'depthperpass', 'travelz', 'feedrate', 'feedrate_z', 'feedrate_rapid',
                      'endz', 'toolchangez']

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
                    custom_offset = self.ui.tool_offset_entry.get_value()
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
                    tool_dia_copy[dia_key] = dict(data_copy)
                    data_copy.clear()

            temp_tools_dict.update({
                tooluid_key: dict(tool_dia_copy)
            })
            tool_dia_copy.clear()


        self.tools.clear()
        self.tools = dict(temp_tools_dict)

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
                        spindlespeed=spindlespeed, steps_per_circle=self.app.defaults["cncjob_steps_per_circle"])

        FlatCAMObj.__init__(self, name)

        self.kind = "cncjob"

        self.options.update({
            "plot": True,
            "tooldia": 0.03937,  # 0.4mm in inches
            "append": "",
            "prepend": "",
            "dwell": False,
            "dwelltime": 1,
            "type": 'Geometry'
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

        # for now it show if the plot will be done for multi-tool CNCJob (True) or for single tool
        # (like the one in the TCL Command), False
        self.multitool = False

        # used for parsing the GCode lines to adjust the offset when the GCode was offseted
        offsetx_re_string = r'(?=.*(X[-\+]?\d*\.\d*))'
        self.g_offsetx_re = re.compile(offsetx_re_string)
        offsety_re_string = r'(?=.*(Y[-\+]?\d*\.\d*))'
        self.g_offsety_re = re.compile(offsety_re_string)
        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from predecessors.
        self.ser_attrs += ['options', 'kind', 'cnc_tools', 'multitool']

        self.annotation = self.app.plotcanvas.new_text_group()

    def build_ui(self):
        self.ui_disconnect()

        FlatCAMObj.build_ui(self)

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

        self.form_fields.update({
            "plot": self.ui.plot_cb,
            # "tooldia": self.ui.tooldia_entry,
            "append": self.ui.append_text,
            "prepend": self.ui.prepend_text,
        })

        # Fill form fields only on object create
        self.to_form()

        self.ui.updateplot_button.clicked.connect(self.on_updateplot_button_click)
        self.ui.export_gcode_button.clicked.connect(self.on_exportgcode_button_click)
        self.ui.modify_gcode_button.clicked.connect(self.on_modifygcode_button_click)

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

    def on_exportgcode_button_click(self, *args):
        self.app.report_usage("cncjob_on_exportgcode_button")

        self.read_form()

        if 'Roland' in self.pp_excellon_name or 'Roland' in self.pp_geometry_name:
            _filter_ = "RML1 Files (*.rol);;" \
                       "All Files (*.*)"
        else:
            _filter_ = "G-Code Files (*.nc);;G-Code Files (*.txt);;G-Code Files (*.tap);;G-Code Files (*.cnc);;" \
                       "G-Code Files (*.g-code);;All Files (*.*)"
        try:
            filename = str(QtWidgets.QFileDialog.getSaveFileName(
                caption="Export G-Code ...", directory=self.app.get_last_save_folder(), filter=_filter_)[0])
        except TypeError:
            filename = str(QtWidgets.QFileDialog.getSaveFileName(caption="Export G-Code ...", filter=_filter_)[0])

        preamble = str(self.ui.prepend_text.get_value())
        postamble = str(self.ui.append_text.get_value())

        self.export_gcode(filename, preamble=preamble, postamble=postamble)
        self.app.file_saved.emit("gcode", filename)
        self.app.inform.emit("[success] G-Code file saved to: %s" % filename)

    def on_modifygcode_button_click(self, *args):
        # add the tab if it was closed
        self.app.ui.plot_tab_area.addTab(self.app.ui.cncjob_tab, "CNC Code Editor")

        # delete the absolute and relative position and messages in the infobar
        self.app.ui.position_label.setText("")
        self.app.ui.rel_position_label.setText("")

        # Switch plot_area to CNCJob tab
        self.app.ui.plot_tab_area.setCurrentWidget(self.app.ui.cncjob_tab)

        preamble = str(self.ui.prepend_text.get_value())
        postamble = str(self.ui.append_text.get_value())
        self.app.gcode_edited = self.export_gcode(preamble=preamble, postamble=postamble, to_file=True)

        # first clear previous text in text editor (if any)
        self.app.ui.code_editor.clear()

        # then append the text from GCode to the text editor
        for line in self.app.gcode_edited:
            proc_line = str(line).strip('\n')
            self.app.ui.code_editor.append(proc_line)

        self.app.ui.code_editor.moveCursor(QtGui.QTextCursor.Start)

        self.app.handleTextChanged()
        self.app.ui.show()

    def gcode_header(self):
        time_str = "{:%A, %d %B %Y at %H:%M}".format(datetime.now())
        marlin = False
        try:
            for key in self.cnc_tools[0]:
                if self.cnc_tools[0][key]['data']['ppname_g'] == 'marlin':
                    marlin = True
                    break
        except:
            try:
                for key in self.cnc_tools[0]:
                    if self.cnc_tools[0][key]['data']['ppname_e'] == 'marlin':
                        marlin = True
                        break
            except:
                pass

        if marlin is False:

            gcode = '(G-CODE GENERATED BY FLATCAM - www.flatcam.org 2018)\n' + '\n'

            gcode += '(Name: ' + str(self.options['name']) + ')\n'
            gcode += '(Type: ' + "G-code from " + str(self.options['type']) + ')\n'

            # if str(p['options']['type']) == 'Excellon' or str(p['options']['type']) == 'Excellon Geometry':
            #     gcode += '(Tools in use: ' + str(p['options']['Tools_in_use']) + ')\n'

            gcode += '(Units: ' + self.units.upper() + ')\n' + "\n"
            gcode += '(Created on ' + time_str + ')\n' + '\n'

        else:
            gcode = ';G-CODE GENERATED BY FLATCAM - www.flatcam.org 2018\n' + '\n'

            gcode += ';Name: ' + str(self.options['name']) + '\n'
            gcode += ';Type: ' + "G-code from " + str(p['options']['type']) + '\n'

            # if str(p['options']['type']) == 'Excellon' or str(p['options']['type']) == 'Excellon Geometry':
            #     gcode += '(Tools in use: ' + str(p['options']['Tools_in_use']) + ')\n'

            gcode += ';Units: ' + self.units.upper() + '\n' + "\n"
            gcode += ';Created on ' + time_str + '\n' + '\n'

        return gcode

    def export_gcode(self, filename=None, preamble='', postamble='', to_file=False):
        gcode = ''
        roland = False

        # detect if using Roland postprocessor
        try:
            for key in self.cnc_tools:
                if self.cnc_tools[key]['data']['ppname_g'] == 'Roland_MDX_20':
                    roland = True
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
        if roland is False:
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
        else:
            # fix so the preamble gets inserted in between the comments header and the actual start of GCODE
            g_idx = gcode.rfind('G20')

            # if it did not find 'G20' then search for 'G21'
            if g_idx == -1:
                g_idx = gcode.rfind('G21')

            # if it did not find 'G20' and it did not find 'G21' then there is an error and return
            if g_idx == -1:
                self.app.inform.emit("[error_notcl] G-code does not have a units code: either G20 or G21")
                return

            g = gcode[:g_idx] + preamble + '\n' + gcode[g_idx:] + postamble

        # lines = StringIO(self.gcode)
        lines = StringIO(g)

        ## Write
        if filename is not None:
            try:
                with open(filename, 'w') as f:
                    for line in lines:
                        f.write(line)

            except FileNotFoundError:
                self.app.inform.emit("[warning_notcl] No such file or directory")
                return
        elif to_file is False:
            # Just for adding it to the recent files list.
            self.app.file_opened.emit("cncjob", filename)

            self.app.inform.emit("[success] Saved to: " + filename)
        else:
            return lines

    def get_gcode(self, preamble='', postamble=''):
        #we need this to be able get_gcode separatelly for shell command export_gcode
        return preamble + '\n' + self.gcode + "\n" + postamble

    def get_svg(self):
        # we need this to be able get_svg separately for shell command export_svg
        pass

    def on_plot_cb_click(self, *args):
        if self.muted_ui:
            return
        self.plot()
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

        self.shapes.clear(update=True)
        for tooluid_key in self.cnc_tools:
            tooldia = float('%.4f' % float(self.cnc_tools[tooluid_key]['tooldia']))
            gcode_parsed = self.cnc_tools[tooluid_key]['gcode_parsed']
            # tool_uid = int(self.ui.cnc_tools_table.item(cw_row, 3).text())

            if self.ui.cnc_tools_table.cellWidget((tooluid_key - 1), 6).isChecked():
                self.plot2(tooldia=tooldia, obj=self, visible=True, gcode_parsed=gcode_parsed)

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


    def plot(self, visible=None):

        # Does all the required setup and returns False
        # if the 'ptint' option is set to False.
        if not FlatCAMObj.plot(self):
            return

        visible = visible if visible else self.options['plot']

        try:
            if self.multitool is False: # single tool usage
                self.plot2(tooldia=self.options["tooldia"], obj=self, visible=visible)
            else:
                # multiple tools usage
                for tooluid_key in self.cnc_tools:
                    tooldia = float('%.4f' % float(self.cnc_tools[tooluid_key]['tooldia']))
                    gcode_parsed = self.cnc_tools[tooluid_key]['gcode_parsed']
                    self.plot2(tooldia=tooldia, obj=self, visible=visible, gcode_parsed=gcode_parsed)
            self.shapes.redraw()
        except (ObjectDeleted, AttributeError):
            self.shapes.clear(update=True)
            self.annotation.clear(update=True)

    def convert_units(self, units):
        factor = CNCjob.convert_units(self, units)
        FlatCAMApp.App.log.debug("FlatCAMCNCjob.convert_units()")
        self.options["tooldia"] *= factor

# end of file
