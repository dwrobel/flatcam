from tclCommands.TclCommand import TclCommandSignaled
from FlatCAMObj import FlatCAMGeometry

import collections
from copy import deepcopy


class TclCommandCncjob(TclCommandSignaled):
    """
    Tcl shell command to Generates a CNC Job from a Geometry Object.

    example:
        set_sys units MM
        new
        open_gerber tests/gerber_files/simple1.gbr -outname margin
        isolate margin -dia 3
        cncjob margin_iso
    """

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = ['cncjob']

    # dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str)
    ])

    # dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('dia', float),
        ('z_cut', float),
        ('z_move', float),
        ('feedrate', float),
        ('feedrate_z', float),
        ('feedrate_rapid', float),
        ('multidepth', bool),
        ('extracut', bool),
        ('depthperpass', float),
        ('toolchange', int),
        ('toolchangez', float),
        ('toolchangexy', tuple),
        ('startz', float),
        ('endz', float),
        ('spindlespeed', int),
        ('dwell', bool),
        ('dwelltime', float),
        ('pp', str),
        ('muted', int),
        ('outname', str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = []

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Generates a CNC Job from a Geometry Object.",
        'args': collections.OrderedDict([
            ('name', 'Name of the source object.'),
            ('dia', 'Tool diameter to show on screen.'),
            ('z_cut', 'Z-axis cutting position.'),
            ('z_move', 'Z-axis moving position.'),
            ('feedrate', 'Moving speed on X-Y plane when cutting.'),
            ('feedrate_z', 'Moving speed on Z plane when cutting.'),
            ('feedrate_rapid', 'Rapid moving at speed when cutting.'),
            ('multidepth', 'Use or not multidepth cnc cut. (True or False)'),
            ('extracut', 'Use or not an extra cnccut over the first point in path,in the job end (example: True)'),
            ('depthperpass', 'Height of one layer for multidepth.'),
            ('toolchange', 'Enable tool changes (example: True).'),
            ('toolchangez', 'Z distance for toolchange (example: 30.0).'),
            ('toolchangexy', 'X, Y coordonates for toolchange in format (x, y) (example: (2.0, 3.1) ).'),
            ('startz', 'Height before the first move.'),
            ('endz', 'Height where the last move will park.'),
            ('spindlespeed', 'Speed of the spindle in rpm (example: 4000).'),
            ('dwell', 'True or False; use (or not) the dwell'),
            ('dwelltime', 'Time to pause to allow the spindle to reach the full speed'),
            ('outname', 'Name of the resulting Geometry object.'),
            ('pp', 'Name of the Geometry preprocessor. No quotes, case sensitive'),
            ('muted', 'It will not put errors in the Shell.')
        ]),
        'examples': ['cncjob geo_name -dia 0.5 -z_cut -1.7 -z_move 2 -feedrate 120 -pp default']
    }

    def execute(self, args, unnamed_args):
        """
        execute current TCL shell command

        :param args: array of known named arguments and options
        :param unnamed_args: array of other values which were passed into command
            without -somename and  we do not have them in known arg_names
        :return: None or exception
        """

        name = ''

        if 'muted' in args:
            muted = args['muted']
        else:
            muted = 0

        try:
            name = args['name']
        except KeyError:
            if muted == 0:
                self.raise_tcl_error("Object name is missing")
            else:
                return "fail"

        if 'outname' not in args:
            args['outname'] = str(name) + "_cnc"

        obj = self.app.collection.get_by_name(str(name), isCaseSensitive=False)

        if obj is None:
            if muted == 0:
                self.raise_tcl_error("Object not found: %s" % str(name))
            else:
                return "fail"

        if not isinstance(obj, FlatCAMGeometry):
            if muted == 0:
                self.raise_tcl_error('Expected FlatCAMGeometry, got %s %s.' % (str(name), type(obj)))
            else:
                return

        args["dia"] = args["dia"] if "dia" in args and args["dia"] else obj.options["cnctooldia"]

        args["z_cut"] = args["z_cut"] if "z_cut" in args and args["z_cut"] else obj.options["cutz"]
        args["z_move"] = args["z_move"] if "z_move" in args and args["z_move"] else obj.options["travelz"]

        args["feedrate"] = args["feedrate"] if "feedrate" in args and args["feedrate"] else obj.options["feedrate"]
        args["feedrate_z"] = args["feedrate_z"] if "feedrate_z" in args and args["feedrate_z"] else \
            obj.options["feedrate_z"]
        args["feedrate_rapid"] = args["feedrate_rapid"] if "feedrate_rapid" in args and args["feedrate_rapid"] else \
            obj.options["feedrate_rapid"]

        args["multidepth"] = bool(args["multidepth"]) if "multidepth" in args else obj.options["multidepth"]
        args["extracut"] = bool(args["extracut"]) if "extracut" in args else obj.options["extracut"]
        args["depthperpass"] = args["depthperpass"] if "depthperpass" in args and args["depthperpass"] else \
            obj.options["depthperpass"]

        args["startz"] = args["startz"] if "startz" in args and args["startz"] else \
            self.app.defaults["geometry_startz"]
        args["endz"] = args["endz"] if "endz" in args and args["endz"] else obj.options["endz"]

        args["spindlespeed"] = args["spindlespeed"] if "spindlespeed" in args and args["spindlespeed"] else None
        args["dwell"] = bool(args["dwell"]) if "dwell" in args else obj.options["dwell"]
        args["dwelltime"] = args["dwelltime"] if "dwelltime" in args and args["dwelltime"] else obj.options["dwelltime"]

        args["pp"] = args["pp"] if "pp" in args and args["pp"] else obj.options["ppname_g"]

        args["toolchange"] = True if "toolchange" in args and args["toolchange"] == 1 else False
        args["toolchangez"] = args["toolchangez"] if "toolchangez" in args and args["toolchangez"] else \
            obj.options["toolchangez"]
        args["toolchangexy"] = args["toolchangexy"] if "toolchangexy" in args and args["toolchangexy"] else \
            self.app.defaults["geometry_toolchangexy"]

        del args['name']

        for arg in args:
            if arg == "toolchange_xy" or arg == "spindlespeed" or arg == "startz":
                continue
            else:
                if args[arg] is None:
                    print(arg, args[arg])
                    if muted == 0:
                        self.raise_tcl_error('One of the command parameters that have to be not None, is None.\n'
                                             'The parameter that is None is in the default values found in the list \n'
                                             'generated by the TclCommand "list_sys geom". or in the arguments.')
                    else:
                        return

        # HACK !!! Should be solved elsewhere!!!
        # default option for multidepth is False
        obj.options['multidepth'] = False

        if not obj.multigeo:
            obj.generatecncjob(use_thread=False, plot=False, **args)
        else:
            # Update the local_tools_dict values with the args value
            local_tools_dict = deepcopy(obj.tools)

            for tool_uid in list(local_tools_dict.keys()):
                if 'data' in local_tools_dict[tool_uid]:
                    local_tools_dict[tool_uid]['data']['cutz'] = args["z_cut"]
                    local_tools_dict[tool_uid]['data']['travelz'] = args["z_move"]
                    local_tools_dict[tool_uid]['data']['feedrate'] = args["feedrate"]
                    local_tools_dict[tool_uid]['data']['feedrate_z'] = args["feedrate_z"]
                    local_tools_dict[tool_uid]['data']['feedrate_rapid'] = args["feedrate_rapid"]
                    local_tools_dict[tool_uid]['data']['multidepth'] = args["multidepth"]
                    local_tools_dict[tool_uid]['data']['extracut'] = args["extracut"]
                    local_tools_dict[tool_uid]['data']['depthperpass'] = args["depthperpass"]
                    local_tools_dict[tool_uid]['data']['toolchange'] = args["toolchange"]
                    local_tools_dict[tool_uid]['data']['toolchangez'] = args["toolchangez"]
                    local_tools_dict[tool_uid]['data']['toolchangexy'] = args["toolchangexy"]
                    local_tools_dict[tool_uid]['data']['startz'] = args["startz"]
                    local_tools_dict[tool_uid]['data']['endz'] = args["endz"]
                    local_tools_dict[tool_uid]['data']['spindlespeed'] = args["spindlespeed"]
                    local_tools_dict[tool_uid]['data']['dwell'] = args["dwell"]
                    local_tools_dict[tool_uid]['data']['dwelltime'] = args["dwelltime"]
                    local_tools_dict[tool_uid]['data']['ppname_g'] = args["pp"]
            obj.mtool_gen_cncjob(
                outname=args['outname'],
                tools_dict=local_tools_dict,
                tools_in_use=[],
                use_thread=False,
                plot=False)
            # self.raise_tcl_error('The object is a multi-geo geometry which is not supported in cncjob Tcl Command')
