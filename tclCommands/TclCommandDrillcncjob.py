from ObjectCollection import *
from tclCommands.TclCommand import TclCommandSignaled


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
        ('tools', str),
        ('drillz', float),
        ('travelz', float),
        ('feedrate', float),
        ('feedrate_rapid', float),
        ('spindlespeed', int),
        ('toolchange', bool),
        ('toolchangez', float),
        ('endz', float),
        ('ppname_e', str),
        ('outname', str),
        ('opt_type', str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Generates a Drill CNC Job from a Excellon Object.",
        'args': collections.OrderedDict([
            ('name', 'Name of the source object.'),
            ('tools', 'Comma separated indexes of tools (example: 1,3 or 2) or select all if not specified.'),
            ('drillz', 'Drill depth into material (example: -2.0).'),
            ('travelz', 'Travel distance above material (example: 2.0).'),
            ('feedrate', 'Drilling feed rate.'),
            ('feedrate_rapid', 'Rapid drilling feed rate.'),
            ('spindlespeed', 'Speed of the spindle in rpm (example: 4000).'),
            ('toolchange', 'Enable tool changes (example: True).'),
            ('toolchangez', 'Z distance for toolchange (example: 30.0).'),
            ('toolchangexy', 'X, Y coordonates for toolchange in format (x, y) (example: (2.0, 3.1) ).'),
            ('endz', 'Z distance at job end (example: 30.0).'),
            ('ppname_e', 'This is the Excellon postprocessor name: case_sensitive, no_quotes'),
            ('outname', 'Name of the resulting Geometry object.'),
            ('opt_type', 'Name of move optimization type. R by default from Rtree or '
                         'T from Travelling Salesman Algorithm')
        ]),
        'examples': ['drillcncjob test.TXT -drillz -1.5 -travelz 14 -feedrate 222 -feedrate_rapid 456 -spindlespeed 777'
                     ' -toolchange True -toolchangez 33 -endz 22 -ppname_e default\n'
                     'Usage of -feedrate_rapid matter only when the posptocessor is using it, like -marlin-.']
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

        if 'outname' not in args:
            args['outname'] = name + "_cnc"

        obj = self.app.collection.get_by_name(name)
        if obj is None:
            self.raise_tcl_error("Object not found: %s" % name)

        if not isinstance(obj, FlatCAMExcellon):
            self.raise_tcl_error('Expected FlatCAMExcellon, got %s %s.' % (name, type(obj)))

        xmin = obj.options['xmin']
        ymin = obj.options['ymin']
        xmax = obj.options['xmax']
        ymax = obj.options['ymax']

        def job_init(job_obj, app_obj):

            drillz = args["drillz"] if "drillz" in args else obj.options["drillz"]
            job_obj.z_move = args["travelz"] if "travelz" in args else obj.options["travelz"]
            job_obj.feedrate = args["feedrate"] if "feedrate" in args else obj.options["feedrate"]
            job_obj.feedrate_rapid = args["feedrate_rapid"] \
                if "feedrate_rapid" in args else obj.options["feedrate_rapid"]

            job_obj.spindlespeed = args["spindlespeed"] if "spindlespeed" in args else None
            job_obj.pp_excellon_name = args["ppname_e"] if "ppname_e" in args \
                else obj.options["ppname_e"]

            job_obj.coords_decimals = int(self.app.defaults["cncjob_coords_decimals"])
            job_obj.fr_decimals = int(self.app.defaults["cncjob_fr_decimals"])

            job_obj.options['type'] = 'Excellon'

            toolchange = True if "toolchange" in args and args["toolchange"] == 1 else False
            toolchangez = args["toolchangez"] if "toolchangez" in args else obj.options["toolchangez"]
            job_obj.toolchangexy = args["toolchangexy"] if "toolchangexy" in args else obj.options["toolchangexy"]

            job_obj.toolchange_xy_type = "excellon"

            job_obj.options['xmin'] = xmin
            job_obj.options['ymin'] = ymin
            job_obj.options['xmax'] = xmax
            job_obj.options['ymax'] = ymax

            endz = args["endz"] if "endz" in args else obj.options["endz"]

            tools = args["tools"] if "tools" in args else 'all'
            opt_type = args["opt_type"] if "opt_type" in args else 'B'

            job_obj.generate_from_excellon_by_tool(obj, tools, drillz=drillz, toolchangez=toolchangez,
                                                   endz=endz,
                                                   toolchange=toolchange, excellon_optimization_type=opt_type)
            job_obj.gcode_parse()
            job_obj.create_geometry()

        self.app.new_object("cncjob", args['outname'], job_init)
