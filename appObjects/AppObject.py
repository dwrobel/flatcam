# ###########################################################
# FlatCAM: 2D Post-processing for Manufacturing             #
# http://flatcam.org                                        #
# Author: Juan Pablo Caram (c)                              #
# Date: 2/5/2014                                            #
# MIT Licence                                               #
# Modified by Marius Stanciu (2020)                         #
# ###########################################################

from PyQt6 import QtCore

from appObjects.CNCJobObject import CNCJobObject
from appObjects.DocumentObject import DocumentObject
from appObjects.ExcellonObject import ExcellonObject
from appObjects.GeometryObject import GeometryObject
from appObjects.GerberObject import GerberObject
from appObjects.ScriptObject import ScriptObject

import time
import traceback
from copy import deepcopy

# FlatCAM Translation
import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class AppObject(QtCore.QObject):

    # Emitted by app_obj.new_object() and passes the new object as argument, plot flag.
    # on_object_created() adds the object to the collection, plots on appropriate flag
    # and emits app_obj.new_object_available.
    object_created = QtCore.pyqtSignal(object, bool, bool, object, list)

    # Emitted when a object has been changed (like scaled, mirrored)
    object_changed = QtCore.pyqtSignal(object)

    # Emitted after object has been plotted.
    # Calls 'on_zoom_fit' method to fit object in scene view in main thread to prevent drawing glitches.
    object_plotted = QtCore.pyqtSignal(object)

    plots_updated = QtCore.pyqtSignal()

    def __init__(self, app):
        super(AppObject, self).__init__()
        self.app = app
        self.inform = app.inform

        # signals that are emitted when object state changes
        self.object_created.connect(self.on_object_created)
        self.object_changed.connect(self.on_object_changed)
        self.object_plotted.connect(self.on_object_plotted)
        self.plots_updated.connect(self.app.on_plots_updated)

    def new_object(self, kind, name, initialize, plot=True, autoselected=True, callback=None,
                   callback_params=None):
        """
        Creates a new specialized FlatCAMObj and attaches it to the application,
        this is, updates the GUI accordingly, any other records and plots it.
        This method is thread-safe.

        Notes:
        If the name is in use, the self.collection will modify it when appending it to the collection.
        There is no need to handle
              name conflicts here.

        :param kind:            The kind of object to create. One of 'gerber', 'excellon', 'cncjob' and 'geometry'
        :type kind:             str
        :param name:            Name for the object
        :type name:             str
        :param initialize:      Function to run after creation of the object but before it is attached to the
                                application
                                The function is called with 2 parameters: the new object and the App instance.
        :type initialize:       function
        :param plot:            If to plot the resulting object
        :param autoselected:    if the resulting object is autoselected in the Project tab and therefore in the
                                self.collection
        :param callback:        a method that is launched after the object is created
        :type callback:         function

        :param callback_params: a list of parameters for the parameter: callback
        :type callback_params:  list

        :return:                Either the object or the string 'fail'
        :rtype:                 object
        """

        if callback_params is None:
            callback_params = [None]
        self.app.log.debug("AppObject.new_object()")
        obj_plot = plot
        obj_autoselected = autoselected

        t0 = time.time()  # Debug

        # ## Create object
        classdict = {
            "gerber":       GerberObject,
            "excellon":     ExcellonObject,
            "cncjob":       CNCJobObject,
            "geometry":     GeometryObject,
            "script":       ScriptObject,
            "document":     DocumentObject
        }

        self.app.log.debug("Calling object constructor...")

        # Object creation/instantiation
        obj = classdict[kind](name)

        # ############################################################################################################
        # adding object PROPERTIES
        # ############################################################################################################
        obj.units = self.app.options["units"]
        obj.isHovering = False
        obj.notHovering = True

        # IMPORTANT
        # The key names in defaults and options dictionaries are not random:
        # they have to have in name first the type of the object (geometry, excellon, cncjob and gerber) or how it's
        # called here, the 'kind' followed by an underline. Above the App default values from self.defaults are
        # copied to self.obj_options. After that, below, depending on the type of
        # object that is created, it will strip the name of the object and the underline (if the original key was
        # let's say "excellon_toolchange", it will strip the excellon_) and to the obj.obj_options the key will become
        # "toolchange"

        # ############################################################################################################
        # this section copies the application defaults related to the object to the object OPTIONS
        # ############################################################################################################
        for option in self.app.options:
            if option.find(kind + "_") == 0:
                oname = option[len(kind) + 1:]
                obj.obj_options[oname] = self.app.options[option]

        # add some of the FlatCAM Tools related properties
        # it is done like this to preserve some kind of order in the keys
        if kind == 'excellon':
            for option in self.app.options:
                if option.find('tools_drill_') == 0:
                    obj.obj_options[option] = self.app.options[option]
        if kind == 'gerber':
            for option in self.app.options:
                if option.find('tools_iso_') == 0:
                    obj.obj_options[option] = self.app.options[option]

        # the milling options should be inherited by all manufacturing objects
        if kind in ['excellon', 'gerber', 'geometry', 'cncjob']:
            for option in self.app.options:
                if option.find('tools_mill_') == 0:
                    obj.obj_options[option] = self.app.options[option]
            for option in self.app.options:
                if option.find('tools_') == 0:
                    obj.obj_options[option] = self.app.options[option]
        # ############################################################################################################
        # ############################################################################################################

        # Initialize as per user request
        # User must take care to implement initialize
        # in a thread-safe way as is likely that we
        # have been invoked in a separate thread.
        t1 = time.time()
        self.app.log.debug("%f seconds before initialize()." % (t1 - t0))

        try:
            return_value = initialize(obj, self.app)
        except Exception as e:
            msg = '[ERROR_NOTCL] %s' % _("An internal error has occurred. See shell.\n")
            msg += _("Object ({kind}) failed because: {error} \n\n").format(kind=kind, error=str(e))
            msg += traceback.format_exc()
            self.app.inform.emit(msg)
            return "fail"

        t2 = time.time()
        msg = "%s %s. %f seconds executing initialize()." % (_("New object with name:"), name, (t2 - t1))
        self.app.log.debug(msg)
        self.app.inform_shell.emit(msg)

        if return_value == 'fail':
            self.app.log.debug("Object (%s) parsing and/or geometry creation failed." % kind)
            return "fail"

        # ############################################################################################################
        # Check units and convert if necessary
        # This condition CAN be true because initialize() can change obj.units
        # ############################################################################################################
        if self.app.options["units"].upper() != obj.units.upper():
            self.app.inform.emit('%s: %s' % (_("Converting units to "), self.app.options["units"]))
            obj.convert_units(self.app.options["units"])
            t3 = time.time()
            self.app.log.debug("%f seconds converting units." % (t3 - t2))

        # ############################################################################################################
        # Create the bounding box for the object and then add the results to the obj.obj_options
        # But not for Scripts or for Documents
        # ############################################################################################################
        if kind != 'document' and kind != 'script':
            try:
                xmin, ymin, xmax, ymax = obj.bounds()
                obj.obj_options['xmin'] = xmin
                obj.obj_options['ymin'] = ymin
                obj.obj_options['xmax'] = xmax
                obj.obj_options['ymax'] = ymax
            except Exception as e:
                self.app.log.error("AppObject.new_object() -> The object has no bounds properties. %s" % str(e))
                return "fail"

        self.app.log.debug("Moving new object back to main thread.")

        # ############################################################################################################
        # Move the object to the main thread and let the app know that it is available.
        # ############################################################################################################
        obj.moveToThread(self.app.main_thread)

        if return_value == 'drill_gx2':
            self.object_created.emit(obj, obj_plot, obj_autoselected, self.app.convert_any2excellon, [name])
            self.app.log.warning("Gerber X2 drill file detected. Converted to Excellon object.")
            self.app.inform.emit('[WARNING] %s' % _("Gerber X2 drill file detected. Converted to Excellon object."))
        else:
            if callback_params is None:
                callback_params = []
            self.object_created.emit(obj, obj_plot, obj_autoselected, callback, callback_params)

        if return_value == "defective":
            return "defective"

        return obj

    def on_object_created(self, obj, plot, auto_select, callback, callback_params):
        """
        Event callback for object creation.
        It will add the new object to the collection. After that it will plot the object in a threaded way

        :param obj:             The newly created FlatCAM object.
        :param plot:            if the newly create object to be plotted
        :param auto_select:     if the newly created object to be autoselected after creation
        :param callback:        a method that is launched after the object is created
        :param callback_params: a list of parameters for the parameter: callback
        :type callback_params:  list
        :return:                None
        """

        t0 = time.time()  # DEBUG
        self.app.log.debug("on_object_created()")

        # #############################################################################################################
        # ###############################  Add the new object to the Collection  ######################################
        # #############################################################################################################
        # The Collection might change the name if there is a collision
        self.app.collection.append(obj)

        # after adding the object to the collection always update the list of objects that are in the collection
        self.app.all_objects_list = self.app.collection.get_list()

        # self.app.inform.emit('[selected] %s created & selected: %s' %
        #                  (str(obj.kind).capitalize(), str(obj.obj_options['name'])))

        # #############################################################################################################
        # ######################  Set colors for the message in the Status Bar  #######################################
        # #############################################################################################################
        if obj.kind == 'gerber':
            self.app.inform.emit('[selected] {kind} {tx}: <span style="color:{color};">{name}</span>'.format(
                kind=obj.kind.capitalize(),
                color='green',
                name=str(obj.obj_options['name']), tx=_("created/selected"))
            )
        elif obj.kind == 'excellon':
            self.app.inform.emit('[selected] {kind} {tx}: <span style="color:{color};">{name}</span>'.format(
                kind=obj.kind.capitalize(),
                color='brown',
                name=str(obj.obj_options['name']), tx=_("created/selected"))
            )
        elif obj.kind == 'cncjob':
            self.app.inform.emit('[selected] {kind} {tx}: <span style="color:{color};">{name}</span>'.format(
                kind=obj.kind.capitalize(),
                color='blue',
                name=str(obj.obj_options['name']), tx=_("created/selected"))
            )
        elif obj.kind == 'geometry':
            self.app.inform.emit('[selected] {kind} {tx}: <span style="color:{color};">{name}</span>'.format(
                kind=obj.kind.capitalize(),
                color='red',
                name=str(obj.obj_options['name']), tx=_("created/selected"))
            )
        elif obj.kind == 'script':
            self.app.inform.emit('[selected] {kind} {tx}: <span style="color:{color};">{name}</span>'.format(
                kind=obj.kind.capitalize(),
                color='orange',
                name=str(obj.obj_options['name']), tx=_("created/selected"))
            )
        elif obj.kind == 'document':
            self.app.inform.emit('[selected] {kind} {tx}: <span style="color:{color};">{name}</span>'.format(
                kind=obj.kind.capitalize(),
                color='darkCyan',
                name=str(obj.obj_options['name']), tx=_("created/selected"))
            )

        # ############################################################################################################
        # Set the colors for the objects that have geometry
        # ############################################################################################################
        if obj.kind in ['excellon', 'gerber']:
            try:
                if obj.kind == 'excellon':
                    if self.app.options["excellon_color"]:
                        obj.fill_color = self.app.options["excellon_color"][0]
                        obj.outline_color = self.app.options["excellon_color"][1]
                    else:
                        obj.fill_color = self.app.options["excellon_plot_fill"]
                        obj.outline_color = self.app.options["excellon_plot_line"]

                if obj.kind == 'gerber':
                    if self.app.options["gerber_store_color_list"] is True:
                        group = self.app.collection.group_items["gerber"]
                        index = group.child_count() - 1

                        # when loading a Gerber object always create a color tuple (line color, fill_color, layer_name)
                        # and add it to the self.app.options["gerber_color_list"] from where it will be picked and used
                        try:
                            colors = self.app.options["gerber_color_list"][index]
                        except IndexError:
                            obj.outline_color = self.app.options["gerber_plot_line"]
                            obj.fill_color = self.app.options["gerber_plot_fill"]
                            obj.alpha_level = str(hex(int(obj.fill_color[7:9], 16))[2:])
                            colors = (obj.outline_color, obj.fill_color, '%s_%d' % (_("Layer"), int(index)))
                            self.app.options["gerber_color_list"].append(colors)

                        new_line_color = colors[0]
                        new_fill = colors[1]
                        new_alpha = str(hex(int(colors[1][7:9], 16))[2:])
                        obj.outline_color = new_line_color
                        obj.fill_color = new_fill
                        obj.alpha_level = new_alpha
                    else:
                        obj.outline_color = self.app.options["gerber_plot_line"]
                        obj.fill_color = self.app.options["gerber_plot_fill"]
                        obj.alpha_level = str(hex(int(self.app.options['gerber_plot_fill'][7:9], 16))[2:])
            except Exception as e:
                self.app.log.error("AppObject.new_object() -> setting colors error. %s" % str(e))

        if auto_select or self.app.ui.notebook.currentWidget() is self.app.ui.properties_tab:
            # select the just opened object but deselect the previous ones
            self.app.collection.set_all_inactive()
            self.app.collection.set_active(obj.obj_options["name"])
        else:
            self.app.collection.set_all_inactive()

        # here it is done the object plotting
        def plotting_task(t_obj):
            with self.app.proc_container.new('%s ...' % _("Plotting")):
                if t_obj.kind == 'cncjob':
                    t_obj.plot(kind=self.app.options["cncjob_plot_kind"])
                elif t_obj.kind == 'gerber':
                    t_obj.plot(color=t_obj.outline_color, face_color=t_obj.fill_color)
                else:
                    t_obj.plot()

                t1 = time.time()  # DEBUG
                msg = "%f seconds adding object and plotting." % (t1 - t0)
                self.app.log.debug(msg)
                self.object_plotted.emit(t_obj)

                if t_obj.kind == 'gerber' and self.app.options["gerber_buffering"] != 'full' and \
                        self.app.options["gerber_delayed_buffering"]:
                    t_obj.do_buffer_signal.emit()

        # Send to worker
        # self.worker.add_task(worker_task, [self])
        if plot is True:
            self.app.worker_task.emit({'fcn': plotting_task, 'params': [obj]})

        if callback is not None:
            # callback(*callback_params)
            self.app.worker_task.emit({'fcn': callback, 'params': callback_params})

    def on_object_changed(self, obj):
        """
        Called whenever the geometry of the object was changed in some way.
        This require the update of it's bounding values so it can be the selected on canvas.
        Update the bounding box data from obj.obj_options

        :param obj: the object that was changed
        :return: None
        """

        try:
            xmin, ymin, xmax, ymax = obj.bounds()
        except TypeError:
            return
        obj.obj_options['xmin'] = xmin
        obj.obj_options['ymin'] = ymin
        obj.obj_options['xmax'] = xmax
        obj.obj_options['ymax'] = ymax

        self.app.log.debug("Object changed, updating the bounding box data on self.obj_options")
        # delete the old selection shape
        self.app.delete_selection_shape()
        self.app.should_we_save = True

    def on_object_plotted(self):
        """
        Callback called whenever the plotted object needs to be fit into the viewport (canvas)

        :return: None
        """
        self.app.on_zoom_fit()

    def new_excellon_object(self, new_name=None):
        """
        Creates a new, blank Excellon object.

        :param new_name:    new name for the new Geometry object
        :type new_name:     str
        :return:            None
        """

        outname = 'new_exc' if new_name is None else new_name

        def obj_init(new_obj, app_obj):
            new_obj.tools = {}
            new_obj.source_file = ''
            new_obj.solid_geometry = []

        self.new_object('excellon', outname, obj_init, plot=False)

    def new_geometry_object(self, new_name=None):
        """
        Creates a new, blank and single-tool Geometry object.

        :param new_name:    new name for the new Geometry object
        :type new_name:     str
        :return:            None
        """

        outname = 'new_geo' if new_name is None else new_name

        def initialize(new_obj, app):
            new_obj.multitool = True
            new_obj.multigeo = True

            # store here the default data for Geometry Data
            default_data = {}
            for opt_key, opt_val in app.options.items():
                if opt_key.find('geometry' + "_") == 0:
                    oname = opt_key[len('geometry') + 1:]
                    default_data[oname] = app.options[opt_key]
                if opt_key.find('tools_') == 0:
                    default_data[opt_key] = app.options[opt_key]

            new_obj.tools = {
                1: {
                    'tooldia':          float(app.options["tools_mill_tooldia"]),
                    'offset':           'Path',
                    'offset_value':     0.0,
                    'type':             'Rough',
                    'tool_type':        'C1',
                    'data':             deepcopy(default_data),
                    'solid_geometry':   []
                }
            }

            new_obj.tools[1]['data']['name'] = outname
            new_obj.solid_geometry = []
            new_obj.source_file = ''

        self.new_object('geometry', outname, initialize, plot=False)

    def new_gerber_object(self, new_name=None):
        """
        Creates a new, blank Gerber object.

        :param new_name:    new name for the new Geometry object
        :type new_name:     str
        :return:            None
        """

        outname = 'new_grb' if new_name is None else new_name

        def initialize(new_obj, app):
            new_obj.multitool = False
            new_obj.source_file = ''
            new_obj.multigeo = False
            new_obj.follow = False
            new_obj.tools = {}
            new_obj.solid_geometry = []
            new_obj.follow_geometry = []

            try:
                new_obj.obj_options['xmin'] = 0
                new_obj.obj_options['ymin'] = 0
                new_obj.obj_options['xmax'] = 0
                new_obj.obj_options['ymax'] = 0
            except KeyError:
                pass

        self.new_object('gerber', outname, initialize, plot=False)

    def new_script_object(self, new_name=None):
        """
        Creates a new, blank TCL Script object.

        :param new_name:    new name for the new Geometry object
        :type new_name:     str
        :return:            None
        """

        outname = 'new_script' if new_name is None else new_name

        # commands_list = "# AddCircle, AddPolygon, AddPolyline, AddRectangle, AlignDrill, " \
        #                 "AlignDrillGrid, Bbox, Bounds, ClearShell, CopperClear,\n" \
        #                 "# Cncjob, Cutout, Delete, Drillcncjob, ExportDXF, ExportExcellon, ExportGcode,\n" \
        #                 "# ExportGerber, ExportSVG, Exteriors, Follow, GeoCutout, GeoUnion, GetNames,\n" \
        #                 "# GetSys, ImportSvg, Interiors, Isolate, JoinExcellon, JoinGeometry, " \
        #                 "ListSys, MillDrills,\n" \
        #                 "# MillSlots, Mirror, New, NewExcellon, NewGeometry, NewGerber, Nregions, " \
        #                 "Offset, OpenExcellon, OpenGCode, OpenGerber, OpenProject,\n" \
        #                 "# Options, Paint, Panelize, PlotAl, PlotObjects, SaveProject, " \
        #                 "SaveSys, Scale, SetActive, SetSys, SetOrigin, Skew, SubtractPoly,\n" \
        #                 "# SubtractRectangle, Version, WriteGCode\n"

        new_source_file = '# %s\n' % _('CREATE A NEW TCL SCRIPT') + \
                          '# %s:\n' % _('TCL Tutorial is here') + \
                          '# https://www.tcl.tk/man/tcl8.5/tutorial/tcltutorial.html\n' + '\n\n' + \
                          '# %s:\n' % _("Commands list")
        new_source_file += '# %s\n\n' % _("Type >help< followed by Run Code for a list of Tcl Commands "
                                          "(displayed in Tcl Shell).")

        def initialize(new_obj, app):
            new_obj.source_file = deepcopy(new_source_file)

        self.new_object('script', outname, initialize, plot=False)

    def new_document_object(self, new_name=None):
        """
        Creates a new, blank Document object.

        :param new_name:    new name for the new Geometry object
        :type new_name:     str
        :return:            None
        """

        outname = 'new_document' if new_name is None else new_name

        def initialize(new_obj, app):
            new_obj.source_file = ""

        self.new_object('document', outname, initialize, plot=False)
