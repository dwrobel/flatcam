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

from appGUI.ObjectUI import *

from appCommon.Common import LoudDict
from appGUI.PlotCanvasLegacy import ShapeCollectionLegacy
from appGUI.VisPyVisuals import ShapeCollection

from shapely.ops import unary_union
from shapely.geometry import Polygon, MultiPolygon

from copy import deepcopy
import sys
import math

import gettext
import appTranslation as fcTranslate
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
    in the appGUI, can be plotted, and their options can be modified
    by the user in their respective forms.
    """

    # Instance of the application to which these are related.
    # The app should set this value.
    app = None

    # signal to plot a single object
    plot_single_object = QtCore.pyqtSignal()

    # signal for Properties
    calculations_finished = QtCore.pyqtSignal(float, float, float, float, float, object)

    def __init__(self, name):
        """
        Constructor.

        :param name: Name of the object given by the user.
        :return: FlatCAMObj
        """

        QtCore.QObject.__init__(self)

        # View
        self.ui = None

        # set True by the collection.append() when the object load is complete
        self.load_complete = None

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
            self.mark_shapes = ShapeCollection(parent=self.app.plotcanvas.view.scene, layers=1)
            # self.shapes = ShapeCollection(parent=self.app.plotcanvas.view.scene, pool=self.app.pool, layers=2)
        else:
            self.shapes = ShapeCollectionLegacy(obj=self, app=self.app, name=name)
            self.mark_shapes = ShapeCollectionLegacy(obj=self, app=self.app, name=name + "_mark_shapes")

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

        # this is the treeWidget from the UI; it is updated when the add_properties_items() method is called
        self.treeWidget = None

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
            self.app.ui.properties_scroll_area.takeWidget()
            # self.ui.scale_entry.returnPressed.connect(self.on_scale_button_click)
        except Exception as e:
            self.app.log.debug("FlatCAMObj.build_ui() --> Nothing to remove: %s" % str(e))

        self.app.ui.properties_scroll_area.setWidget(self.ui)
        # self.ui.setMinimumWidth(100)
        # self.ui.setMaximumWidth(self.app.ui.properties_tab.sizeHint().width())

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
            with self.app.proc_container.new('%s ...' % _("Plotting")):
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
            with self.app.proc_container.new('%s ...' % _("Plotting")):
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
            with self.app.proc_container.new('%s ...' % _("Plotting")):
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
            with self.app.proc_container.new('%s ...' % _("Plotting")):
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

    def add_mark_shape(self, **kwargs):
        if self.deleted:
            raise ObjectDeleted()
        else:
            key = self.mark_shapes.add(tolerance=self.drawing_tolerance, layer=0, **kwargs)
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

    def add_properties_items(self, obj, treeWidget):
        self.treeWidget = treeWidget
        parent = self.treeWidget.invisibleRootItem()
        apertures = ''
        tools = ''
        drills = ''
        slots = ''
        others = ''

        font = QtGui.QFont()
        font.setBold(True)

        p_color = QtGui.QColor("#000000") if self.app.defaults['global_gray_icons'] is False \
            else QtGui.QColor("#FFFFFF")

        # main Items categories
        dims = self.treeWidget.addParent(
            parent, _('Dimensions'), expanded=True, color=p_color, font=font)
        options = self.treeWidget.addParent(parent, _('Options'), color=p_color, font=font)

        if obj.kind.lower() == 'gerber':
            apertures = self.treeWidget.addParent(
                parent, _('Apertures'), expanded=True, color=p_color, font=font)
        else:
            tools = self.treeWidget.addParent(
                parent, _('Tools'), expanded=True, color=p_color, font=font)

        if obj.kind.lower() == 'excellon':
            drills = self.treeWidget.addParent(
                parent, _('Drills'), expanded=True, color=p_color, font=font)
            slots = self.treeWidget.addParent(
                parent, _('Slots'), expanded=True, color=p_color, font=font)

        if obj.kind.lower() == 'cncjob':
            others = self.treeWidget.addParent(
                parent, _('Others'), expanded=True, color=p_color, font=font)

        # separator = self.treeWidget.addParent(parent, '')

        def job_thread(obj_prop):
            self.app.proc_container.new(_("Calculating dimensions ... Please wait."))

            length = 0.0
            width = 0.0
            area = 0.0
            copper_area = 0.0

            geo = obj_prop.solid_geometry
            if geo:
                # calculate physical dimensions
                try:
                    xmin, ymin, xmax, ymax = obj_prop.bounds()

                    length = abs(xmax - xmin)
                    width = abs(ymax - ymin)
                except Exception as ee:
                    log.debug("FlatCAMObj.add_properties_items() -> calculate dimensions --> %s" % str(ee))

                # calculate box area
                if self.app.defaults['units'].lower() == 'mm':
                    area = (length * width) / 100
                else:
                    area = length * width

                if obj_prop.kind.lower() == 'gerber' and geo:
                    # calculate copper area
                    try:
                        for geo_el in geo:
                            copper_area += geo_el.area
                    except TypeError:
                        copper_area += geo.area
                    copper_area /= 100
            else:
                xmin = []
                ymin = []
                xmax = []
                ymax = []

                if obj_prop.kind.lower() == 'cncjob':
                    try:
                        for tool_k in obj_prop.exc_cnc_tools:
                            x0, y0, x1, y1 = unary_union(obj_prop.exc_cnc_tools[tool_k]['solid_geometry']).bounds
                            xmin.append(x0)
                            ymin.append(y0)
                            xmax.append(x1)
                            ymax.append(y1)
                    except Exception as ee:
                        log.debug("FlatCAMObj.add_properties_items() cncjob --> %s" % str(ee))

                    try:
                        for tool_k in obj_prop.cnc_tools:
                            x0, y0, x1, y1 = unary_union(obj_prop.cnc_tools[tool_k]['solid_geometry']).bounds
                            xmin.append(x0)
                            ymin.append(y0)
                            xmax.append(x1)
                            ymax.append(y1)
                    except Exception as ee:
                        log.debug("FlatCAMObj.add_properties_items() cncjob --> %s" % str(ee))
                else:
                    try:
                        if obj_prop.tools:
                            for tool_k in obj_prop.tools:
                                t_geo = obj_prop.tools[tool_k]['solid_geometry']
                                try:
                                    x0, y0, x1, y1 = unary_union(t_geo).bounds
                                except Exception:
                                    continue
                                xmin.append(x0)
                                ymin.append(y0)
                                xmax.append(x1)
                                ymax.append(y1)
                    except Exception as ee:
                        log.debug("FlatCAMObj.add_properties_items() not cncjob tools --> %s" % str(ee))

                if xmin and ymin and xmax and ymax:
                    xmin = min(xmin)
                    ymin = min(ymin)
                    xmax = max(xmax)
                    ymax = max(ymax)

                    length = abs(xmax - xmin)
                    width = abs(ymax - ymin)

                    # calculate box area
                    if self.app.defaults['units'].lower() == 'mm':
                        area = (length * width) / 100
                    else:
                        area = length * width

                if obj_prop.kind.lower() == 'gerber' and obj_prop.tools:
                    # calculate copper area

                    # create a complete solid_geometry from the tools
                    geo_tools = []
                    for tool_k in obj_prop.tools:
                        if 'solid_geometry' in obj_prop.tools[tool_k]:
                            for geo_el in obj_prop.tools[tool_k]['solid_geometry']:
                                geo_tools.append(geo_el)

                    for geo_el in geo_tools:
                        copper_area += geo_el.area
                    # in cm2
                    copper_area /= 100

            area_chull = 0.0
            if obj_prop.kind.lower() != 'cncjob':
                # calculate and add convex hull area
                if geo:
                    if isinstance(geo, list) and geo[0] is not None:
                        if isinstance(geo, MultiPolygon):
                            env_obj = geo.convex_hull
                        elif (isinstance(geo, MultiPolygon) and len(geo) == 1) or \
                                (isinstance(geo, list) and len(geo) == 1) and isinstance(geo[0], Polygon):
                            env_obj = unary_union(geo)
                            env_obj = env_obj.convex_hull
                        else:
                            env_obj = unary_union(geo)
                            env_obj = env_obj.convex_hull

                        area_chull = env_obj.area
                    else:
                        area_chull = 0
                else:
                    try:
                        area_chull = None
                        if obj_prop.tools:
                            area_chull_list = []
                            for tool_k in obj_prop.tools:
                                area_el = unary_union(obj_prop.tools[tool_k]['solid_geometry']).convex_hull
                                area_chull_list.append(area_el.area)
                            area_chull = max(area_chull_list)
                    except Exception as er:
                        area_chull = None
                        log.debug("FlatCAMObj.add_properties_items() area chull--> %s" % str(er))

            if self.app.defaults['units'].lower() == 'mm' and area_chull:
                area_chull = area_chull / 100

            if area_chull is None:
                area_chull = 0

            self.calculations_finished.emit(area, length, width, area_chull, copper_area, dims)

        self.app.worker_task.emit({'fcn': job_thread, 'params': [obj]})

        # Options items
        for option in obj.options:
            if option == 'name':
                continue
            self.treeWidget.addChild(options, [str(option), str(obj.options[option])], True)

        # Items that depend on the object type
        if obj.kind.lower() == 'gerber' and obj.apertures:
            temp_ap = {}
            for ap in obj.apertures:
                temp_ap.clear()
                temp_ap = deepcopy(obj.apertures[ap])
                temp_ap.pop('geometry', None)

                solid_nr = 0
                follow_nr = 0
                clear_nr = 0

                if 'geometry' in obj.apertures[ap]:
                    if obj.apertures[ap]['geometry']:
                        font.setBold(True)
                        for el in obj.apertures[ap]['geometry']:
                            if 'solid' in el:
                                solid_nr += 1
                            if 'follow' in el:
                                follow_nr += 1
                            if 'clear' in el:
                                clear_nr += 1
                else:
                    font.setBold(False)
                temp_ap['Solid_Geo'] = '%s Polygons' % str(solid_nr)
                temp_ap['Follow_Geo'] = '%s LineStrings' % str(follow_nr)
                temp_ap['Clear_Geo'] = '%s Polygons' % str(clear_nr)

                apid = self.treeWidget.addParent(
                    apertures, str(ap), expanded=False, color=p_color, font=font)
                for key in temp_ap:
                    self.treeWidget.addChild(apid, [str(key), str(temp_ap[key])], True)
        elif obj.kind.lower() == 'excellon':
            tot_drill_cnt = 0
            tot_slot_cnt = 0

            for tool, value in obj.tools.items():
                toolid = self.treeWidget.addParent(
                    tools, str(tool), expanded=False, color=p_color, font=font)

                drill_cnt = 0  # variable to store the nr of drills per tool
                slot_cnt = 0  # variable to store the nr of slots per tool

                # Find no of drills for the current tool
                if 'drills' in value and value['drills']:
                    drill_cnt = len(value['drills'])

                tot_drill_cnt += drill_cnt

                # Find no of slots for the current tool
                if 'slots' in value and value['slots']:
                    slot_cnt = len(value['slots'])

                tot_slot_cnt += slot_cnt

                self.treeWidget.addChild(
                    toolid,
                    [
                        _('Diameter'),
                        '%.*f %s' % (self.decimals, value['tooldia'], self.app.defaults['units'].lower())
                    ],
                    True
                )
                self.treeWidget.addChild(toolid, [_('Drills number'), str(drill_cnt)], True)
                self.treeWidget.addChild(toolid, [_('Slots number'), str(slot_cnt)], True)

            self.treeWidget.addChild(drills, [_('Drills total number:'), str(tot_drill_cnt)], True)
            self.treeWidget.addChild(slots, [_('Slots total number:'), str(tot_slot_cnt)], True)
        elif obj.kind.lower() == 'geometry':
            for tool, value in obj.tools.items():
                geo_tool = self.treeWidget.addParent(
                    tools, str(tool), expanded=False, color=p_color, font=font)
                for k, v in value.items():
                    if k == 'solid_geometry':
                        # printed_value = _('Present') if v else _('None')
                        try:
                            printed_value = str(len(v))
                        except (TypeError, AttributeError):
                            printed_value = '1'
                        self.treeWidget.addChild(geo_tool, [str(k), printed_value], True)
                    elif k == 'data':
                        tool_data = self.treeWidget.addParent(
                            geo_tool, str(k).capitalize(), color=p_color, font=font)
                        for data_k, data_v in v.items():
                            self.treeWidget.addChild(tool_data, [str(data_k), str(data_v)], True)
                    else:
                        self.treeWidget.addChild(geo_tool, [str(k), str(v)], True)
        elif obj.kind.lower() == 'cncjob':
            # for cncjob objects made from gerber or geometry
            for tool, value in obj.cnc_tools.items():
                geo_tool = self.treeWidget.addParent(
                    tools, str(tool), expanded=False, color=p_color, font=font)
                for k, v in value.items():
                    if k == 'solid_geometry':
                        printed_value = _('Present') if v else _('None')
                        self.treeWidget.addChild(geo_tool, [_("Solid Geometry"), printed_value], True)
                    elif k == 'gcode':
                        printed_value = _('Present') if v != '' else _('None')
                        self.treeWidget.addChild(geo_tool, [_("GCode Text"), printed_value], True)
                    elif k == 'gcode_parsed':
                        printed_value = _('Present') if v else _('None')
                        self.treeWidget.addChild(geo_tool, [_("GCode Geometry"), printed_value], True)
                    elif k == 'data':
                        pass
                    else:
                        self.treeWidget.addChild(geo_tool, [str(k), str(v)], True)

                v = value['data']
                tool_data = self.treeWidget.addParent(
                    geo_tool, _("Tool Data"), color=p_color, font=font)
                for data_k, data_v in v.items():
                    self.treeWidget.addChild(tool_data, [str(data_k).capitalize(), str(data_v)], True)

            # for cncjob objects made from excellon
            for tool_dia, value in obj.exc_cnc_tools.items():
                exc_tool = self.treeWidget.addParent(
                    tools, str(value['tool']), expanded=False, color=p_color, font=font
                )
                self.treeWidget.addChild(
                    exc_tool,
                    [
                        _('Diameter'),
                        '%.*f %s' % (self.decimals, tool_dia, self.app.defaults['units'].lower())
                    ],
                    True
                )
                for k, v in value.items():
                    if k == 'solid_geometry':
                        printed_value = _('Present') if v else _('None')
                        self.treeWidget.addChild(exc_tool, [_("Solid Geometry"), printed_value], True)
                    elif k == 'nr_drills':
                        self.treeWidget.addChild(exc_tool, [_("Drills number"), str(v)], True)
                    elif k == 'nr_slots':
                        self.treeWidget.addChild(exc_tool, [_("Slots number"), str(v)], True)
                    elif k == 'gcode':
                        printed_value = _('Present') if v != '' else _('None')
                        self.treeWidget.addChild(exc_tool, [_("GCode Text"), printed_value], True)
                    elif k == 'gcode_parsed':
                        printed_value = _('Present') if v else _('None')
                        self.treeWidget.addChild(exc_tool, [_("GCode Geometry"), printed_value], True)
                    else:
                        pass

                self.treeWidget.addChild(
                    exc_tool,
                    [
                        _("Depth of Cut"),
                        '%.*f %s' % (
                            self.decimals,
                            (obj.z_cut - abs(value['data']['tools_drill_offset'])),
                            self.app.defaults['units'].lower()
                        )
                    ],
                    True
                )
                self.treeWidget.addChild(
                    exc_tool,
                    [
                        _("Clearance Height"),
                        '%.*f %s' % (
                            self.decimals,
                            obj.z_move,
                            self.app.defaults['units'].lower()
                        )
                    ],
                    True
                )
                self.treeWidget.addChild(
                    exc_tool,
                    [
                        _("Feedrate"),
                        '%.*f %s/min' % (
                            self.decimals,
                            obj.feedrate,
                            self.app.defaults['units'].lower()
                        )
                    ],
                    True
                )

                v = value['data']
                tool_data = self.treeWidget.addParent(
                    exc_tool, _("Tool Data"), color=p_color, font=font)
                for data_k, data_v in v.items():
                    self.treeWidget.addChild(tool_data, [str(data_k).capitalize(), str(data_v)], True)

            r_time = obj.routing_time
            if r_time > 1:
                units_lbl = 'min'
            else:
                r_time *= 60
                units_lbl = 'sec'
            r_time = math.ceil(float(r_time))
            self.treeWidget.addChild(
                others,
                [
                    '%s:' % _('Routing time'),
                    '%.*f %s' % (self.decimals, r_time, units_lbl)],
                True
            )
            self.treeWidget.addChild(
                others,
                [
                    '%s:' % _('Travelled distance'),
                    '%.*f %s' % (self.decimals, obj.travel_distance, self.app.defaults['units'].lower())
                ],
                True
            )

        # treeWidget.addChild(separator, [''])

    def update_area_chull(self, area, length, width, chull_area, copper_area, location):

        # add dimensions
        self.treeWidget.addChild(
            location,
            ['%s:' % _('Length'), '%.*f %s' % (self.decimals, length, self.app.defaults['units'].lower())],
            True
        )
        self.treeWidget.addChild(
            location,
            ['%s:' % _('Width'), '%.*f %s' % (self.decimals, width, self.app.defaults['units'].lower())],
            True
        )

        # add box area
        if self.app.defaults['units'].lower() == 'mm':
            self.treeWidget.addChild(location, ['%s:' % _('Box Area'), '%.*f %s' % (self.decimals, area, 'cm2')], True)
            self.treeWidget.addChild(
                location,
                ['%s:' % _('Convex_Hull Area'), '%.*f %s' % (self.decimals, chull_area, 'cm2')],
                True
            )

        else:
            self.treeWidget.addChild(location, ['%s:' % _('Box Area'), '%.*f %s' % (self.decimals, area, 'in2')], True)
            self.treeWidget.addChild(
                location,
                ['%s:' % _('Convex_Hull Area'), '%.*f %s' % (self.decimals, chull_area, 'in2')],
                True
            )

        # add copper area
        if self.app.defaults['units'].lower() == 'mm':
            self.treeWidget.addChild(
                location, ['%s:' % _('Copper Area'), '%.*f %s' % (self.decimals, copper_area, 'cm2')], True)
        else:
            self.treeWidget.addChild(
                location, ['%s:' % _('Copper Area'), '%.*f %s' % (self.decimals, copper_area, 'in2')], True)

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

        def task(visibility):
            if visibility is True:
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
