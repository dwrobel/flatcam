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

import inspect  # TODO: For debugging only.

from AppGUI.ObjectUI import *

from Common import LoudDict
from AppGUI.PlotCanvasLegacy import ShapeCollectionLegacy

import sys

import gettext
import AppTranslation as fcTranslate
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


class FlatCAMObj(QtCore.QObject):
    """
    Base type of objects handled in FlatCAM. These become interactive
    in the AppGUI, can be plotted, and their options can be modified
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

        self.mark_shapes = {}

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
                              "have all attributes in the latest application version." % str(attr))
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

        try:
            self.ui.transformations_button.clicked.connect(self.app.transform_tool.run)
        except (TypeError, AttributeError):
            pass

        # self.ui.skew_button.clicked.connect(self.on_skew_button_click)

    def build_ui(self):
        """
        Sets up the UI/form for this object. Show the UI in the App.

        :return: None
        """

        self.muted_ui = True
        log.debug(str(inspect.stack()[1][3]) + "--> FlatCAMObj.build_ui()")

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
        # self.ui.setMinimumWidth(100)
        # self.ui.setMaximumWidth(self.app.ui.selected_tab.sizeHint().width())

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
            except Exception:
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
        self.app.defaults.report_usage("obj_on_offset_button")

        self.read_form()
        vector_val = self.ui.offsetvector_entry.get_value()

        def worker_task():
            with self.app.proc_container.new(_("Offsetting...")):
                self.offset(vector_val)
            self.app.proc_container.update_view_text('')
            with self.app.proc_container.new('%s...' % _("Plotting")):
                self.plot()
            self.app.app_obj.object_changed.emit(self)

        self.app.worker_task.emit({'fcn': worker_task, 'params': []})

    def on_scale_button_click(self):
        self.read_form()
        try:
            factor = float(self.ui.scale_entry.get_value())
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
            self.app.app_obj.object_changed.emit(self)

        self.app.worker_task.emit({'fcn': worker_task, 'params': []})

    def on_skew_button_click(self):
        self.app.defaults.report_usage("obj_on_skew_button")
        self.read_form()
        x_angle = self.ui.xangle_entry.get_value()
        y_angle = self.ui.yangle_entry.get_value()

        def worker_task():
            with self.app.proc_container.new(_("Skewing...")):
                self.skew(x_angle, y_angle)
            self.app.proc_container.update_view_text('')
            with self.app.proc_container.new('%s...' % _("Plotting")):
                self.plot()
            self.app.app_obj.object_changed.emit(self)

        self.app.worker_task.emit({'fcn': worker_task, 'params': []})

    def to_form(self):
        """
        Copies options to the UI form.

        :return: None
        """
        log.debug(str(inspect.stack()[1][3]) + " --> FlatCAMObj.to_form()")
        for option in self.options:
            try:
                self.set_form_item(option)
            except Exception as err:
                self.app.log.warning("Unexpected error: %s" % str(sys.exc_info()), str(err))

    def read_form(self):
        """
        Reads form into ``self.options``.

        :return: None
        :rtype: None
        """
        log.debug(str(inspect.stack()[1][3]) + "--> FlatCAMObj.read_form()")
        for option in self.options:
            try:
                self.read_form_item(option)
            except Exception:
                self.app.log.warning("Unexpected error: %s" % str(sys.exc_info()))

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

    def plot(self, kind=None):
        """
        Plot this object (Extend this method to implement the actual plotting).
        Call this in descendants before doing the plotting.

        :param kind:    Used by only some of the FlatCAM objects
        :return:        Whether to continue plotting or not depending on the "plot" option. Boolean
        """
        log.debug(str(inspect.stack()[1][3]) + " --> FlatCAMObj.plot()")

        if self.deleted:
            return False

        self.clear()
        return True

    def single_object_plot(self):
        def plot_task():
            with self.app.proc_container.new('%s...' % _("Plotting")):
                self.plot()
            self.app.app_obj.object_changed.emit(self)

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

        :param last_ext:        The file extension that was last used to save a file
        :param filter_string:   A key in self.app.defaults that holds a string with the filter from QFileDialog
        used when saving a file
        :return:                None
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

        current_visibility = self.shapes.visible
        # self.shapes.visible = value   # maybe this is slower in VisPy? use enabled property?

        def task(current_visibility):
            if current_visibility is True:
                if value is False:
                    self.shapes.visible = False
            else:
                if value is True:
                    self.shapes.visible = True

            if self.app.is_legacy is False:
                # Not all object types has annotations
                try:
                    self.annotation.visible = value
                except Exception:
                    pass

        if threaded:
            self.app.worker_task.emit({'fcn': task, 'params': [current_visibility]})
        else:
            task(current_visibility)

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