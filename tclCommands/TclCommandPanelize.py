from tclCommands.TclCommand import TclCommand

import shapely.affinity as affinity

import logging
from copy import deepcopy
import collections

log = logging.getLogger('base')


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

        def panelize_2():
            if obj is not None:
                self.app.inform.emit("Generating panel ... Please wait.")

                def job_init_excellon(obj_fin, app_obj):
                    currenty = 0.0

                    obj_fin.tools = obj.tools.copy()
                    if 'drills' not in obj_fin.tools:
                        obj_fin.tools['drills'] = []
                    if 'slots' not in obj_fin.tools:
                        obj_fin.tools['slots'] = []
                    if 'solid_geometry' not in obj_fin.tools:
                        obj_fin.tools['solid_geometry'] = []

                    for option in obj.options:
                        if option != 'name':
                            try:
                                obj_fin.options[option] = obj.options[option]
                            except Exception as e:
                                app_obj.log.warning("Failed to copy option: %s" % str(option))
                                app_obj.log.debug("TclCommandPanelize.execute().panelize2() --> %s" % str(e))

                    for row in range(rows):
                        currentx = 0.0
                        for col in range(columns):
                            if 'drills' in obj.tools:
                                for drill_pt in obj.tools['drills']:
                                    point_offseted = affinity.translate(drill_pt, currentx, currenty)
                                    obj_fin.tools['drills'].append(point_offseted)
                            if 'slots' in obj.tools:
                                for slot_tuple in obj.tools['slots']:
                                    start_offseted = affinity.translate(slot_tuple[0], currentx, currenty)
                                    stop_offseted = affinity.translate(slot_tuple[1], currentx, currenty)
                                    obj_fin.tools['slots'].append(
                                        (start_offseted, stop_offseted)
                                    )
                            currentx += lenghtx
                        currenty += lenghty

                    obj_fin.create_geometry()
                    obj_fin.zeros = obj.zeros
                    obj_fin.units = obj.units

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

                    if obj.kind == 'geometry':
                        obj_fin.multigeo = obj.multigeo
                        obj_fin.tools = deepcopy(obj.tools)
                        if obj.multigeo is True:
                            for tool in obj.tools:
                                obj_fin.tools[tool]['solid_geometry'][:] = []

                    for row in range(rows):
                        currentx = 0.0

                        for col in range(columns):
                            if obj.kind == 'geometry':
                                if obj.multigeo is True:
                                    for tool in obj.tools:
                                        obj_fin.tools[tool]['solid_geometry'].append(translate_recursion(
                                            obj.tools[tool]['solid_geometry'])
                                        )
                                else:
                                    obj_fin.solid_geometry.append(
                                        translate_recursion(obj.solid_geometry)
                                    )
                            else:
                                obj_fin.solid_geometry.append(
                                    translate_recursion(obj.solid_geometry)
                                )

                            currentx += lenghtx
                        currenty += lenghty

                if obj.kind == 'excellon':
                    self.app.app_obj.new_object("excellon", outname, job_init_excellon, plot=False, autoselected=True)
                else:
                    self.app.app_obj.new_object("geometry", outname, job_init_geometry, plot=False, autoselected=True)

        if threaded is True:
            self.app.proc_container.new(_("Working ..."))

            def job_thread(app_obj):
                try:
                    panelize_2()
                    app_obj.inform.emit('[success]' % _("Done."))
                except Exception as ee:
                    log.debug(str(ee))
                    return

            self.app.collection.promise(outname)
            self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})
        else:
            panelize_2()
            self.app.inform.emit('[success]' % _("Done."))
