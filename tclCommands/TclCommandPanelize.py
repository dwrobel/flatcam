from tclCommands.TclCommand import TclCommand
from FlatCAMObj import FlatCAMGeometry, FlatCAMExcellon

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
    aliases = ['panelize','pan', 'panel']

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
        ('threaded', int)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name', 'rows', 'columns']

    # structured help for current command, args needs to be ordered
    help = {
        'main': 'Rectangular panelizing.',
        'args': collections.OrderedDict([
            ('name', 'Name of the object to panelize.'),
            ('box', 'Name of object which acts as box (cutout for example.)'
                    'for cutout boundary. Object from name is used if not specified.'),
            ('spacing_columns', 'Spacing between columns.'),
            ('spacing_rows', 'Spacing between rows.'),
            ('columns', 'Number of columns.'),
            ('rows', 'Number of rows;'),
            ('outname', 'Name of the new geometry object.'),
            ('threaded', '0 = non-threaded || 1 = threaded')
        ]),
        'examples': []
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
        except Exception as e:
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

        if 'columns' not in args or 'rows' not in args:
            return "ERROR: Specify -columns and -rows"

        if 'outname' in args:
            outname = args['outname']
        else:
            outname = name + '_panelized'

        if 'threaded' in args:
            threaded = args['threaded']
        else:
            threaded = 0

        if 'spacing_columns' in args:
            spacing_columns = args['spacing_columns']
        else:
            spacing_columns = 5

        if 'spacing_rows' in args:
            spacing_rows = args['spacing_rows']
        else:
            spacing_rows = 5

        rows = args['rows']
        columns = args['columns']

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
        #         FlatCAMGeometry.merge(objs, obj_init)
        #
        #     def initialize_excellon(obj_init, app):
        #         # merge expects tools to exist in the target object
        #         obj_init.tools = obj.tools.copy()
        #         FlatCAMExcellon.merge(objs, obj_init)
        #
        #     objs = []
        #     if obj is not None:
        #
        #         for row in range(rows):
        #             currentx = 0
        #             for col in range(columns):
        #                 local_outname = outname + ".tmp." + str(col) + "." + str(row)
        #                 if isinstance(obj, FlatCAMExcellon):
        #                     self.app.new_object("excellon", local_outname, initialize_local_excellon, plot=False,
        #                                         autoselected=False)
        #                 else:
        #                     self.app.new_object("geometry", local_outname, initialize_local, plot=False,
        #                                         autoselected=False)
        #
        #                 currentx += lenghtx
        #             currenty += lenghty
        #
        #         if isinstance(obj, FlatCAMExcellon):
        #             self.app.new_object("excellon", outname, initialize_excellon)
        #         else:
        #             self.app.new_object("geometry", outname, initialize_geometry)
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

                self.app.progress.emit(0)

                def job_init_excellon(obj_fin, app_obj):
                    currenty = 0.0
                    self.app.progress.emit(10)
                    obj_fin.tools = obj.tools.copy()
                    obj_fin.drills = []
                    obj_fin.slots = []
                    obj_fin.solid_geometry = []

                    for option in obj.options:
                        if option is not 'name':
                            try:
                                obj_fin.options[option] = obj.options[option]
                            except Exception as e:
                                log.warning("Failed to copy option: %s" % str(option))
                                log.debug("TclCommandPanelize.execute().panelize2() --> %s" % str(e))

                    for row in range(rows):
                        currentx = 0.0
                        for col in range(columns):
                            if obj.drills:
                                for tool_dict in obj.drills:
                                    point_offseted = affinity.translate(tool_dict['point'], currentx, currenty)
                                    obj_fin.drills.append(
                                        {
                                            "point": point_offseted,
                                            "tool": tool_dict['tool']
                                        }
                                    )
                            if obj.slots:
                                for tool_dict in obj.slots:
                                    start_offseted = affinity.translate(tool_dict['start'], currentx, currenty)
                                    stop_offseted = affinity.translate(tool_dict['stop'], currentx, currenty)
                                    obj_fin.slots.append(
                                        {
                                            "start": start_offseted,
                                            "stop": stop_offseted,
                                            "tool": tool_dict['tool']
                                        }
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
                            geoms = list()
                            for local_geom in geom:
                                geoms.append(translate_recursion(local_geom))
                            return geoms
                        else:
                            return affinity.translate(geom, xoff=currentx, yoff=currenty)

                    obj_fin.solid_geometry = []

                    if isinstance(obj, FlatCAMGeometry):
                        obj_fin.multigeo = obj.multigeo
                        obj_fin.tools = deepcopy(obj.tools)
                        if obj.multigeo is True:
                            for tool in obj.tools:
                                obj_fin.tools[tool]['solid_geometry'][:] = []

                    self.app.progress.emit(0)
                    for row in range(rows):
                        currentx = 0.0

                        for col in range(columns):
                            if isinstance(obj, FlatCAMGeometry):
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

                if isinstance(obj, FlatCAMExcellon):
                    self.app.progress.emit(50)
                    self.app.new_object("excellon", outname, job_init_excellon, plot=False, autoselected=True)
                else:
                    self.app.progress.emit(50)
                    self.app.new_object("geometry", outname, job_init_geometry, plot=False, autoselected=True)

        if threaded == 1:
            proc = self.app.proc_container.new("Generating panel ... Please wait.")

            def job_thread(app_obj):
                try:
                    panelize_2()
                    self.app.inform.emit("[success] Panel created successfully.")
                except Exception as ee:
                    proc.done()
                    log.debug(str(ee))
                    return
                proc.done()

            self.app.collection.promise(outname)
            self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})
        else:
            panelize_2()
            self.app.inform.emit("[success] Panel created successfully.")
