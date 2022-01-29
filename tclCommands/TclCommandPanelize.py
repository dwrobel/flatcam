from tclCommands.TclCommand import TclCommand

import shapely.affinity as affinity
from shapely.geometry import MultiPolygon, MultiLineString

import logging
from copy import deepcopy
import collections

import gettext
import appTranslation as fcTranslate
import builtins

log = logging.getLogger('base')

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class TclCommandPanelize(TclCommand):
    """
    Tcl shell command to panelize an object.

    example:

    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['panelize', 'pan', 'panel']

    description = '%s %s' % ("--", "Create a new object with an array of duplicates of the original geometry, "
                                   "arranged in a grid.")

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str),
    ])

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('rows', int),
        ('columns', int),
        ('spacing_columns', float),
        ('spacing_rows', float),
        ('box', str),
        ('outname', str),
        ('use_thread', str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': 'Create a new object with an array of duplicates of the original geometry, arranged in a grid.',
        'args': collections.OrderedDict([
            ('name', 'Name of the object to panelize.'),
            ('box', 'Name of object which acts as box (cutout for example.)'
                    'for cutout boundary. Object from name is used if not specified.'),
            ('spacing_columns', 'Spacing between columns.'),
            ('spacing_rows', 'Spacing between rows.'),
            ('columns', 'Number of columns.'),
            ('rows', 'Number of rows;'),
            ('outname', 'Name of the new geometry object.'),
            ('use_thread', 'False (0) = non-threaded execution or True (1) = threaded execution')
        ]),
        'examples': [
            'panelize obj_name',

            'panel obj_name -rows 2 -columns 2 -spacing_columns 0.4 -spacing_rows 1.3 -box box_obj_name '
            '-outname panelized_name',

            'panel obj_name -columns 2 -box box_obj_name -outname panelized_name',
        ]
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """

        name = args['name']

        # Get source object.
        try:
            obj = self.app.collection.get_by_name(str(name))
        except Exception:
            return "Could not retrieve object: %s" % name

        if obj is None:
            return "Object not found: %s" % name

        if 'box' in args:
            boxname = args['box']
            try:
                box = self.app.collection.get_by_name(boxname)
            except Exception:
                return "Could not retrieve object: %s" % name
        else:
            box = obj

        if 'columns' in args:
            columns = int(args['columns'])
        else:
            columns = int(0)

        if 'rows' in args:
            rows = int(args['rows'])
        else:
            rows = int(0)

        if 'columns' not in args and 'rows' not in args:
            return "ERROR: Specify either -columns or -rows. The one not specified it will assumed to be 0"

        if 'outname' in args:
            outname = args['outname']
        else:
            outname = name + '_panelized'

        if 'use_thread' in args:
            try:
                par = args['use_thread'].capitalize()
            except AttributeError:
                par = args['use_thread']
            threaded = bool(eval(par))
        else:
            threaded = False

        if 'spacing_columns' in args:
            spacing_columns = int(args['spacing_columns'])
        else:
            spacing_columns = 5

        if 'spacing_rows' in args:
            spacing_rows = int(args['spacing_rows'])
        else:
            spacing_rows = 5

        xmin, ymin, xmax, ymax = box.bounds()
        lenghtx = xmax - xmin + spacing_columns
        lenghty = ymax - ymin + spacing_rows

        # def panelize():
        #     currenty = 0
        #
        #     def initialize_local(obj_init, app):
        #         obj_init.solid_geometry = obj.solid_geometry
        #         obj_init.offset([float(currentx), float(currenty)])
        #         objs.append(obj_init)
        #
        #     def initialize_local_excellon(obj_init, app):
        #         obj_init.tools = obj.tools
        #         # drills are offset, so they need to be deep copied
        #         obj_init.drills = deepcopy(obj.drills)
        #         obj_init.offset([float(currentx), float(currenty)])
        #         obj_init.create_geometry()
        #         objs.append(obj_init)
        #
        #     def initialize_geometry(obj_init, app):
        #         GeometryObject.merge(objs, obj_init)
        #
        #     def initialize_excellon(obj_init, app):
        #         # merge expects tools to exist in the target object
        #         obj_init.tools = obj.tools.copy()
        #         ExcellonObject.merge(objs, obj_init)
        #
        #     objs = []
        #     if obj is not None:
        #
        #         for row in range(rows):
        #             currentx = 0
        #             for col in range(columns):
        #                 local_outname = outname + ".tmp." + str(col) + "." + str(row)
        #                 if isinstance(obj, ExcellonObject):
        #                     self.app.app_obj.new_object("excellon", local_outname, initialize_local_excellon,
        #                                           plot=False,
        #                                         autoselected=False)
        #                 else:
        #                     self.app.app_obj.new_object("geometry", local_outname, initialize_local, plot=False,
        #                                         autoselected=False)
        #
        #                 currentx += lenghtx
        #             currenty += lenghty
        #
        #         if isinstance(obj, ExcellonObject):
        #             self.app.app_obj.new_object("excellon", outname, initialize_excellon)
        #         else:
        #             self.app.app_obj.new_object("geometry", outname, initialize_geometry)
        #
        #         # deselect all  to avoid  delete selected object when run  delete  from  shell
        #         self.app.collection.set_all_inactive()
        #         for delobj in objs:
        #             self.app.collection.set_active(delobj.options['name'])
        #             self.app.on_delete()
        #     else:
        #         return "fail"
        #
        # ret_value = panelize()
        # if ret_value == 'fail':
        #     return 'fail'

        # ############################################################################################################
        # make a copy of the panelized Excellon or Geometry tools
        # ############################################################################################################
        if obj.kind == 'excellon' or obj.kind == 'geometry':
            copied_tools = {}
            for tt, tt_val in list(obj.tools.items()):
                copied_tools[tt] = deepcopy(tt_val)

        # ############################################################################################################
        # make a copy of the panelized Gerber apertures
        # ############################################################################################################
        if obj.kind == 'gerber':
            copied_apertures = {}
            for tt, tt_val in list(obj.tools.items()):
                copied_apertures[tt] = deepcopy(tt_val)

        def panelize_handler():
            if obj is not None:
                self.app.inform.emit("Generating panel ... Please wait.")

                def job_init_excellon(obj_fin, app_obj):
                    obj_fin.multitool = True

                    currenty = 0.0
                    # init the storage for drills and for slots
                    for tool in copied_tools:
                        copied_tools[tool]['drills'] = []
                        copied_tools[tool]['slots'] = []
                    obj_fin.tools = copied_tools
                    obj_fin.solid_geometry = []

                    for option in obj.options:
                        if option != 'name':
                            try:
                                obj_fin.options[option] = obj.options[option]
                            except Exception as e:
                                app_obj.log.error("Failed to copy option: %s" % str(option))
                                app_obj.log.error(
                                    "TclCommandPanelize.execute().panelize2.job_init_excellon() Options:--> %s" %
                                    str(e))

                    # calculate the total number of drills and slots
                    geo_len_drills = 0
                    geo_len_slots = 0
                    for tool in copied_tools:
                        geo_len_drills += len(copied_tools[tool]['drills'])
                        geo_len_slots += len(copied_tools[tool]['slots'])

                    # panelization
                    for row in range(rows):
                        currentx = 0.0
                        for col in range(columns):
                            for tool in obj.tools:
                                if 'drills' in obj.tools[tool]:
                                    if obj.tools[tool]['drills']:
                                        for drill in obj.tools[tool]['drills']:
                                            # offset / panelization
                                            point_offseted = affinity.translate(drill, currentx, currenty)
                                            obj_fin.tools[tool]['drills'].append(point_offseted)
                                else:
                                    obj.tools[tool]['drills'] = []

                                if 'slots' in obj.tools[tool]:
                                    if obj.tools[tool]['slots']:
                                        for slot in obj.tools[tool]['slots']:
                                            # offset / panelization
                                            start_offseted = affinity.translate(slot[0], currentx, currenty)
                                            stop_offseted = affinity.translate(slot[1], currentx, currenty)
                                            offseted_slot = (
                                                start_offseted,
                                                stop_offseted
                                            )
                                            obj_fin.tools[tool]['slots'].append(offseted_slot)
                                else:
                                    obj.tools[tool]['slots'] = []

                            currentx += lenghtx
                        currenty += lenghty

                    obj_fin.create_geometry()
                    obj_fin.zeros = obj.zeros
                    obj_fin.units = obj.units
                    app_obj.inform.emit('%s' % _("Generating panel ... Adding the source code."))
                    obj_fin.source_file = app_obj.f_handlers.export_excellon(obj_name=outname, filename=None,
                                                                             local_use=obj_fin, use_thread=False)

                def job_init_geometry(obj_fin, app_obj):
                    currentx = 0.0
                    currenty = 0.0

                    def translate_recursion(geom):
                        if type(geom) == list:
                            geoms = []
                            for local_geom in geom:
                                geoms.append(translate_recursion(local_geom))
                            return geoms
                        else:
                            return affinity.translate(geom, xoff=currentx, yoff=currenty)

                    obj_fin.solid_geometry = []

                    # create the initial structure on which to create the panel
                    obj_fin.multigeo = obj.multigeo
                    obj_fin.tools = copied_tools
                    if obj.multigeo is True:
                        for tool in obj.tools:
                            obj_fin.tools[tool]['solid_geometry'][:] = []

                    for row in range(rows):
                        currentx = 0.0
                        for col in range(columns):
                            if obj.multigeo is True:
                                for tool in obj.tools:
                                    trans_geo = translate_recursion(obj.tools[tool]['solid_geometry'])
                                    try:
                                        work_geo = trans_geo.geoms if \
                                            isinstance(trans_geo, (MultiPolygon, MultiLineString)) else trans_geo
                                        for trans_it in work_geo:
                                            if not trans_it.is_empty:
                                                obj_fin.tools[tool]['solid_geometry'].append(trans_it)
                                    except TypeError:
                                        if not trans_geo.is_empty:
                                            obj_fin.tools[tool]['solid_geometry'].append(trans_geo)

                                    # #############################################################################
                                    # ##########   Panelize the solid_geometry - always done  #####################
                                    # #############################################################################
                                    try:
                                        sol_geo = obj.solid_geometry
                                        work_geo = sol_geo.geoms if \
                                            isinstance(sol_geo, (MultiPolygon, MultiLineString)) else sol_geo
                                        for geo_el in work_geo:
                                            trans_geo = translate_recursion(geo_el)
                                            obj_fin.solid_geometry.append(trans_geo)
                                    except TypeError:
                                        trans_geo = translate_recursion(obj.solid_geometry)
                                        obj_fin.solid_geometry.append(trans_geo)
                            else:
                                obj_fin.solid_geometry.append(
                                    translate_recursion(obj.solid_geometry)
                                )

                            currentx += lenghtx
                        currenty += lenghty
                    obj_fin.source_file = app_obj.f_handlers.export_dxf(obj_name=outname, filename=None,
                                                                        local_use=obj_fin, use_thread=False)

                def job_init_gerber(obj_fin, app_obj):
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
                            return affinity.translate(geom, xoff=currentx, yoff=currenty)

                    obj_fin.solid_geometry = []

                    # create the initial structure on which to create the panel
                    obj_fin.tools = copied_apertures
                    for ap in obj_fin.tools:
                        obj_fin.tools[ap]['geometry'] = []

                    for row in range(rows):
                        currentx = 0.0
                        for col in range(columns):
                            # Will panelize a Gerber Object
                            for apid in obj.tools:
                                if 'geometry' in obj.tools[apid]:
                                    # panelization -> apertures
                                    for el in obj.tools[apid]['geometry']:
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
                                        obj_fin.tools[apid]['geometry'].append(deepcopy(new_el))

                            # #####################################################################################
                            # ##########   Panelize the solid_geometry - always done  #############################
                            # #####################################################################################
                            try:
                                for geo_el in obj.solid_geometry:
                                    trans_geo = translate_recursion(geo_el)
                                    obj_fin.solid_geometry.append(trans_geo)
                            except TypeError:
                                trans_geo = translate_recursion(obj.solid_geometry)
                                obj_fin.solid_geometry.append(trans_geo)

                            currentx += lenghtx
                        currenty += lenghty

                    obj_fin.source_file = app_obj.f_handlers.export_gerber(obj_name=outname, filename=None,
                                                                           local_use=obj_fin, use_thread=False)

                if obj.kind == 'excellon':
                    self.app.app_obj.new_object("excellon", outname, job_init_excellon, plot=False, autoselected=True)
                elif obj.kind == 'geometry':
                    self.app.app_obj.new_object("geometry", outname, job_init_geometry, plot=False, autoselected=True)
                else:
                    self.app.app_obj.new_object("gerber", outname, job_init_gerber, plot=False, autoselected=True)
        if threaded is True:
            self.app.proc_container.new('%s...' % _("Working"))

            def job_thread(app_obj):
                try:
                    panelize_handler()
                    app_obj.inform.emit('[success] %s' % _("Done."))
                except Exception as err:
                    app_obj.log.error('TclCommandPanelize.execute.job_thread() -> %s' % str(err))
                    return

            self.app.collection.promise(outname)
            self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})
        else:
            try:
                panelize_handler()
                self.app.inform.emit('[success] %s' % _("Done."))
            except Exception as ee:
                self.app.log.error('TclCommandPanelize.execute() non-threaded -> %s' % str(ee))
