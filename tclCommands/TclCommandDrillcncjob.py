from tclCommands.TclCommand import TclCommandSignaled
from FlatCAMObj import FlatCAMExcellon

import collections
import math


class TclCommandDrillcncjob(TclCommandSignaled):
    """
    Tcl shell command to Generates a Drill CNC Job from a Excellon Object.
    """

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = ['drillcncjob']

    # dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str)
    ])

    # dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('drilled_dias', str),
        ('drillz', float),
        ('travelz', float),
        ('feedrate', float),
        ('feedrate_rapid', float),
        ('spindlespeed', int),
        ('toolchangez', float),
        ('toolchangexy', tuple),
        ('endz', float),
        ('dwelltime', float),
        ('pp', str),
        ('outname', str),
        ('opt_type', str),
        ('diatol', float),
        ('muted', int)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Generates a Drill CNC Job from a Excellon Object.",
        'args': collections.OrderedDict([
            ('name', 'Name of the source object.'),
            ('drilled_dias',
             'Comma separated tool diameters of the drills to be drilled (example: 0.6,1.0 or 3.125). '
             'No space allowed'),
            ('drillz', 'Drill depth into material (example: -2.0).'),
            ('travelz', 'Travel distance above material (example: 2.0).'),
            ('feedrate', 'Drilling feed rate.'),
            ('feedrate_rapid', 'Rapid drilling feed rate.'),
            ('spindlespeed', 'Speed of the spindle in rpm (example: 4000).'),
            ('toolchangez', 'Z distance for toolchange (example: 30.0).\n'
                            'If used in the command then a toolchange event will be included in gcode'),
            ('toolchangexy', 'X, Y coordonates for toolchange in format (x, y) (example: (2.0, 3.1) ).'),
            ('endz', 'Z distance at job end (example: 30.0).'),
            ('dwelltime', 'Time to pause to allow the spindle to reach the full speed.\n'
                          'If it is not used in command then it will not be included'),
            ('pp', 'This is the Excellon preprocessor name: case_sensitive, no_quotes'),
            ('outname', 'Name of the resulting Geometry object.'),
            ('opt_type', 'Name of move optimization type. B by default for Basic OR-Tools, M for Metaheuristic OR-Tools'
                         'T from Travelling Salesman Algorithm. B and M works only for 64bit version of FlatCAM and '
                         'T works only for 32bit version of FlatCAM'),
            ('diatol', 'Tolerance. Percentange (0.0 ... 100.0) within which dias in drilled_dias will be judged to be '
                       'the same as the ones in the tools from the Excellon object. E.g: if in drill_dias we have a '
                       'diameter with value 1.0, in the Excellon we have a tool with dia = 1.05 and we set a tolerance '
                       'diatol = 5.0 then the drills with the dia = (0.95 ... 1.05) '
                       'in Excellon will be processed. Float number.'),
            ('muted', 'It will not put errors in the Shell or status bar.')
        ]),
        'examples': ['drillcncjob test.TXT -drillz -1.5 -travelz 14 -feedrate 222 -feedrate_rapid 456 -spindlespeed 777'
                     ' -toolchangez 33 -endz 22 -pp default\n'
                     'Usage of -feedrate_rapid matter only when the preprocessor is using it, like -marlin-.']
    }

    def execute(self, args, unnamed_args):
        """
        execute current TCL shell command

        :param args: array of known named arguments and options
        :param unnamed_args: array of other values which were passed into command
            without -somename and  we do not have them in known arg_names
        :return: None or exception
        """

        name = args['name']

        obj = self.app.collection.get_by_name(name)

        if 'outname' not in args:
            args['outname'] = name + "_cnc"

        if 'muted' in args:
            muted = bool(args['muted'])
        else:
            muted = False

        if obj is None:
            if muted is False:
                self.raise_tcl_error("Object not found: %s" % name)
            else:
                return "fail"

        if not isinstance(obj, FlatCAMExcellon):
            if muted == 0:
                self.raise_tcl_error('Expected FlatCAMExcellon, got %s %s.' % (name, type(obj)))
            else:
                return "fail"

        xmin = obj.options['xmin']
        ymin = obj.options['ymin']
        xmax = obj.options['xmax']
        ymax = obj.options['ymax']

        def job_init(job_obj, app_obj):
            # tools = args["tools"] if "tools" in args else 'all'

            try:
                if 'drilled_dias' in args and args['drilled_dias'] != 'all':
                    diameters = [x.strip() for x in args['drilled_dias'].split(",") if x != '']
                    nr_diameters = len(diameters)

                    req_tools = set()
                    for tool in obj.tools:
                        for req_dia in diameters:
                            obj_dia_form = float('%.*f' % (obj.decimals, float(obj.tools[tool]["C"])))
                            req_dia_form = float('%.*f' % (obj.decimals, float(req_dia)))

                            if 'diatol' in args:
                                tolerance = args['diatol'] / 100

                                tolerance = 0.0 if tolerance < 0.0 else tolerance
                                tolerance = 1.0 if tolerance > 1.0 else tolerance
                                if math.isclose(obj_dia_form, req_dia_form, rel_tol=tolerance):
                                    req_tools.add(tool)
                                    nr_diameters -= 1
                            else:
                                if obj_dia_form == req_dia_form:
                                    req_tools.add(tool)
                                    nr_diameters -= 1

                    if nr_diameters > 0:
                        if muted == 0:
                            self.raise_tcl_error("One or more tool diameters of the drills to be drilled passed to the "
                                                 "TclCommand are not actual tool diameters in the Excellon object.")
                        else:
                            return "fail"

                    # make a string of diameters separated by comma; this is what generate_from_excellon_by_tool() is
                    # expecting as tools parameter
                    tools = ','.join(req_tools)

                    # no longer needed
                    del args['drilled_dias']
                    del args['diatol']

                    # Split and put back. We are passing the whole dictionary later.
                    # args['milled_dias'] = [x.strip() for x in args['tools'].split(",")]
                else:
                    tools = 'all'
            except Exception as e:
                tools = 'all'

                if muted == 0:
                    self.raise_tcl_error("Bad tools: %s" % str(e))
                else:
                    return "fail"

            drillz = args["drillz"] if "drillz" in args and args["drillz"] is not None else obj.options["drillz"]

            if "toolchangez" in args:
                toolchange = True
                if args["toolchangez"] is not None:
                    toolchangez = args["toolchangez"]
                else:
                    toolchangez = obj.options["toolchangez"]
            else:
                toolchange = False
                toolchangez = 0.0

            endz = args["endz"] if "endz" in args and args["endz"] is not None else obj.options["endz"]
            opt_type = args["opt_type"] if "opt_type" in args and args["opt_type"] else 'B'

            job_obj.z_move = args["travelz"] if "travelz" in args and args["travelz"] else obj.options["travelz"]
            job_obj.feedrate = args["feedrate"] if "feedrate" in args and args["feedrate"] else obj.options["feedrate"]
            job_obj.feedrate_rapid = args["feedrate_rapid"] \
                if "feedrate_rapid" in args and args["feedrate_rapid"] else obj.options["feedrate_rapid"]

            if 'dwelltime' in args:
                job_obj.dwell = True
                if args['dwelltime'] is not None:
                    job_obj.dwelltime = float(args['dwelltime'])
                else:
                    job_obj.dwelltime = float(obj.options["dwelltime"])
            else:
                job_obj.dwell = False
                job_obj.dwelltime = 0.0

            job_obj.spindlespeed = args["spindlespeed"] if "spindlespeed" in args else None
            job_obj.pp_excellon_name = args["pp"] if "pp" in args and args["pp"] \
                else obj.options["ppname_e"]

            job_obj.coords_decimals = int(self.app.defaults["cncjob_coords_decimals"])
            job_obj.fr_decimals = int(self.app.defaults["cncjob_fr_decimals"])

            job_obj.options['type'] = 'Excellon'

            job_obj.toolchangexy = args["toolchangexy"] if "toolchangexy" in args and args["toolchangexy"] else \
                obj.options["toolchangexy"]

            job_obj.toolchange_xy_type = "excellon"

            job_obj.options['xmin'] = xmin
            job_obj.options['ymin'] = ymin
            job_obj.options['xmax'] = xmax
            job_obj.options['ymax'] = ymax

            job_obj.generate_from_excellon_by_tool(obj, tools, drillz=drillz, toolchangez=toolchangez, endz=endz,
                                                   toolchange=toolchange, excellon_optimization_type=opt_type)

            for t_item in job_obj.exc_cnc_tools:
                job_obj.exc_cnc_tools[t_item]['data']['offset'] = \
                    float(job_obj.exc_cnc_tools[t_item]['offset_z']) + float(drillz)
                job_obj.exc_cnc_tools[t_item]['data']['ppname_e'] = obj.options['ppname_e']

                # for now there is no tool offset support in this Tcl Command so we write the 0.0 value here
                job_obj.tool_offset[t_item] = 0.0

            job_obj.origin_kind = 'excellon'

            job_obj.gcode_parse()
            job_obj.create_geometry()

        self.app.new_object("cncjob", args['outname'], job_init, plot=False)
