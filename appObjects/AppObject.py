# ###########################################################
# FlatCAM: 2D Post-processing for Manufacturing             #
# http://flatcam.org                                        #
# Author: Juan Pablo Caram (c)                              #
# Date: 2/5/2014                                            #
# MIT Licence                                               #
# Modified by Marius Stanciu (2020)                         #
# ###########################################################

from PyQt5 import QtCore
from appObjects.ObjectCollection import *
from appObjects.FlatCAMCNCJob import CNCJobObject
from appObjects.FlatCAMDocument import DocumentObject
from appObjects.FlatCAMExcellon import ExcellonObject
from appObjects.FlatCAMGeometry import GeometryObject
from appObjects.FlatCAMGerber import GerberObject
from appObjects.FlatCAMScript import ScriptObject

import time
import traceback

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
    object_created = QtCore.pyqtSignal(object, bool, bool)

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

    def new_object(self, kind, name, initialize, plot=True, autoselected=True):
        """
        Creates a new specialized FlatCAMObj and attaches it to the application,
        this is, updates the GUI accordingly, any other records and plots it.
        This method is thread-safe.

        Notes:
            * If the name is in use, the self.collection will modify it
              when appending it to the collection. There is no need to handle
              name conflicts here.

        :param kind: The kind of object to create. One of 'gerber', 'excellon', 'cncjob' and 'geometry'.
        :type kind: str
        :param name: Name for the object.
        :type name: str
        :param initialize: Function to run after creation of the object but before it is attached to the application.
        The function is called with 2 parameters: the new object and the App instance.
        :type initialize: function
        :param plot: If to plot the resulting object
        :param autoselected: if the resulting object is autoselected in the Project tab and therefore in the
        self.collection
        :return: None
        :rtype: None
        """

        log.debug("AppObject.new_object()")
        obj_plot = plot
        obj_autoselected = autoselected

        t0 = time.time()  # Debug

        # ## Create object
        classdict = {
            "gerber": GerberObject,
            "excellon": ExcellonObject,
            "cncjob": CNCJobObject,
            "geometry": GeometryObject,
            "script": ScriptObject,
            "document": DocumentObject
        }

        log.debug("Calling object constructor...")

        # Object creation/instantiation
        obj = classdict[kind](name)

        obj.units = self.app.options["units"]

        # IMPORTANT
        # The key names in defaults and options dictionary's are not random:
        # they have to have in name first the type of the object (geometry, excellon, cncjob and gerber) or how it's
        # called here, the 'kind' followed by an underline. Above the App default values from self.defaults are
        # copied to self.options. After that, below, depending on the type of
        # object that is created, it will strip the name of the object and the underline (if the original key was
        # let's say "excellon_toolchange", it will strip the excellon_) and to the obj.options the key will become
        # "toolchange"

        for option in self.app.options:
            if option.find(kind + "_") == 0:
                oname = option[len(kind) + 1:]
                obj.options[oname] = self.app.options[option]

        obj.isHovering = False
        obj.notHovering = True

        # Initialize as per user request
        # User must take care to implement initialize
        # in a thread-safe way as is is likely that we
        # have been invoked in a separate thread.
        t1 = time.time()
        log.debug("%f seconds before initialize()." % (t1 - t0))
        try:
            return_value = initialize(obj, self.app)
        except Exception as e:
            msg = '[ERROR_NOTCL] %s' % _("An internal error has occurred. See shell.\n")
            msg += _("Object ({kind}) failed because: {error} \n\n").format(kind=kind, error=str(e))
            msg += traceback.format_exc()
            self.app.inform.emit(msg)
            return "fail"

        t2 = time.time()
        log.debug("%f seconds executing initialize()." % (t2 - t1))

        if return_value == 'fail':
            log.debug("Object (%s) parsing and/or geometry creation failed." % kind)
            return "fail"

        # Check units and convert if necessary
        # This condition CAN be true because initialize() can change obj.units
        if self.app.options["units"].upper() != obj.units.upper():
            self.app.inform.emit('%s: %s' % (_("Converting units to "), self.app.options["units"]))
            obj.convert_units(self.app.options["units"])
            t3 = time.time()
            log.debug("%f seconds converting units." % (t3 - t2))

        # Create the bounding box for the object and then add the results to the obj.options
        # But not for Scripts or for Documents
        if kind != 'document' and kind != 'script':
            try:
                xmin, ymin, xmax, ymax = obj.bounds()
                obj.options['xmin'] = xmin
                obj.options['ymin'] = ymin
                obj.options['xmax'] = xmax
                obj.options['ymax'] = ymax
            except Exception as e:
                log.warning("AppObject.new_object() -> The object has no bounds properties. %s" % str(e))
                return "fail"

            try:
                if kind == 'excellon':
                    obj.fill_color = self.app.defaults["excellon_plot_fill"]
                    obj.outline_color = self.app.defaults["excellon_plot_line"]

                if kind == 'gerber':
                    obj.fill_color = self.app.defaults["gerber_plot_fill"]
                    obj.outline_color = self.app.defaults["gerber_plot_line"]
            except Exception as e:
                log.warning("AppObject.new_object() -> setting colors error. %s" % str(e))

        # update the KeyWords list with the name of the file
        self.app.myKeywords.append(obj.options['name'])

        log.debug("Moving new object back to main thread.")

        # Move the object to the main thread and let the app know that it is available.
        obj.moveToThread(self.app.main_thread)
        self.object_created.emit(obj, obj_plot, obj_autoselected)

        return obj

    def new_excellon_object(self):
        """
        Creates a new, blank Excellon object.

        :return: None
        """

        self.new_object('excellon', 'new_exc', lambda x, y: None, plot=False)

    def new_geometry_object(self):
        """
        Creates a new, blank and single-tool Geometry object.

        :return: None
        """

        def initialize(obj, app):
            obj.multitool = False

        self.new_object('geometry', 'new_geo', initialize, plot=False)

    def new_gerber_object(self):
        """
        Creates a new, blank Gerber object.

        :return: None
        """

        def initialize(grb_obj, app):
            grb_obj.multitool = False
            grb_obj.source_file = []
            grb_obj.multigeo = False
            grb_obj.follow = False
            grb_obj.apertures = {}
            grb_obj.solid_geometry = []

            try:
                grb_obj.options['xmin'] = 0
                grb_obj.options['ymin'] = 0
                grb_obj.options['xmax'] = 0
                grb_obj.options['ymax'] = 0
            except KeyError:
                pass

        self.new_object('gerber', 'new_grb', initialize, plot=False)

    def new_script_object(self):
        """
        Creates a new, blank TCL Script object.

        :return: None
        """

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

        new_source_file = '# %s\n' % _('CREATE A NEW FLATCAM TCL SCRIPT') + \
                          '# %s:\n' % _('TCL Tutorial is here') + \
                          '# https://www.tcl.tk/man/tcl8.5/tutorial/tcltutorial.html\n' + '\n\n' + \
                          '# %s:\n' % _("FlatCAM commands list")
        new_source_file += '# %s\n\n' % _("Type >help< followed by Run Code for a list of FlatCAM Tcl Commands "
                                          "(displayed in Tcl Shell).")

        def initialize(obj, app):
            obj.source_file = deepcopy(new_source_file)

        outname = 'new_script'
        self.new_object('script', outname, initialize, plot=False)

    def new_document_object(self):
        """
        Creates a new, blank Document object.

        :return: None
        """

        def initialize(obj, app):
            obj.source_file = ""

        self.new_object('document', 'new_document', initialize, plot=False)

    def on_object_created(self, obj, plot, auto_select):
        """
        Event callback for object creation.
        It will add the new object to the collection. After that it will plot the object in a threaded way

        :param obj: The newly created FlatCAM object.
        :param plot: if the newly create object t obe plotted
        :param auto_select: if the newly created object to be autoselected after creation
        :return: None
        """
        t0 = time.time()  # DEBUG
        log.debug("on_object_created()")

        # The Collection might change the name if there is a collision
        self.app.collection.append(obj)

        # after adding the object to the collection always update the list of objects that are in the collection
        self.app.all_objects_list = self.app.collection.get_list()

        # self.app.inform.emit('[selected] %s created & selected: %s' %
        #                  (str(obj.kind).capitalize(), str(obj.options['name'])))
        if obj.kind == 'gerber':
            self.app.inform.emit('[selected] {kind} {tx}: <span style="color:{color};">{name}</span>'.format(
                kind=obj.kind.capitalize(),
                color='green',
                name=str(obj.options['name']), tx=_("created/selected"))
            )
        elif obj.kind == 'excellon':
            self.app.inform.emit('[selected] {kind} {tx}: <span style="color:{color};">{name}</span>'.format(
                kind=obj.kind.capitalize(),
                color='brown',
                name=str(obj.options['name']), tx=_("created/selected"))
            )
        elif obj.kind == 'cncjob':
            self.app.inform.emit('[selected] {kind} {tx}: <span style="color:{color};">{name}</span>'.format(
                kind=obj.kind.capitalize(),
                color='blue',
                name=str(obj.options['name']), tx=_("created/selected"))
            )
        elif obj.kind == 'geometry':
            self.app.inform.emit('[selected] {kind} {tx}: <span style="color:{color};">{name}</span>'.format(
                kind=obj.kind.capitalize(),
                color='red',
                name=str(obj.options['name']), tx=_("created/selected"))
            )
        elif obj.kind == 'script':
            self.app.inform.emit('[selected] {kind} {tx}: <span style="color:{color};">{name}</span>'.format(
                kind=obj.kind.capitalize(),
                color='orange',
                name=str(obj.options['name']), tx=_("created/selected"))
            )
        elif obj.kind == 'document':
            self.app.inform.emit('[selected] {kind} {tx}: <span style="color:{color};">{name}</span>'.format(
                kind=obj.kind.capitalize(),
                color='darkCyan',
                name=str(obj.options['name']), tx=_("created/selected"))
            )

        # update the SHELL auto-completer model with the name of the new object
        self.app.shell._edit.set_model_data(self.app.myKeywords)

        if auto_select:
            # select the just opened object but deselect the previous ones
            self.app.collection.set_all_inactive()
            self.app.collection.set_active(obj.options["name"])
        else:
            self.app.collection.set_all_inactive()

        # here it is done the object plotting
        def task(t_obj):
            with self.app.proc_container.new(_("Plotting")):
                if t_obj.kind == 'cncjob':
                    t_obj.plot(kind=self.app.defaults["cncjob_plot_kind"])
                else:
                    t_obj.plot()

                t1 = time.time()  # DEBUG
                log.debug("%f seconds adding object and plotting." % (t1 - t0))
                self.object_plotted.emit(t_obj)

                if t_obj.kind == 'gerber' and self.app.defaults["gerber_delayed_buffering"] != 'full' and \
                        self.app.defaults["gerber_delayed_buffering"]:
                    t_obj.do_buffer_signal.emit()

        # Send to worker
        # self.worker.add_task(worker_task, [self])
        if plot is True:
            self.app.worker_task.emit({'fcn': task, 'params': [obj]})

    def on_object_changed(self, obj):
        """
        Called whenever the geometry of the object was changed in some way.
        This require the update of it's bounding values so it can be the selected on canvas.
        Update the bounding box data from obj.options

        :param obj: the object that was changed
        :return: None
        """

        try:
            xmin, ymin, xmax, ymax = obj.bounds()
        except TypeError:
            return
        obj.options['xmin'] = xmin
        obj.options['ymin'] = ymin
        obj.options['xmax'] = xmax
        obj.options['ymax'] = ymax

        log.debug("Object changed, updating the bounding box data on self.options")
        # delete the old selection shape
        self.app.delete_selection_shape()
        self.app.should_we_save = True

    def on_object_plotted(self):
        """
        Callback called whenever the plotted object needs to be fit into the viewport (canvas)

        :return: None
        """
        self.app.on_zoom_fit()
