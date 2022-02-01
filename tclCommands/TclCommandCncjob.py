from tclCommands.TclCommand import TclCommandSignaled

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

    description = '%s %s' % ("--", "Generates a CNC Job object from a Geometry Object.")

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
        ('extracut_length', float),
        ('dpp', float),
        ('toolchangez', float),
        ('toolchangexy', str),
        ('startz', float),
        ('endz', float),
        ('endxy', str),
        ('spindlespeed', int),
        ('dwelltime', float),
        ('las_power', float),
        ('las_min_pwr', float),
        ('pp', str),
        ('muted', str),
        ('outname', str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = []

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Generates a CNC Job object from a Geometry Object.",
        'args': collections.OrderedDict([
            ('name', 'Name of the source object.'),
            ('dia', 'Tool diameter to show on screen.'),
            ('z_cut', 'Z-axis cutting position.'),
            ('z_move', 'Z-axis moving position.'),
            ('feedrate', 'Moving speed on X-Y plane when cutting.'),
            ('feedrate_z', 'Moving speed on Z plane when cutting.'),
            ('feedrate_rapid', 'Rapid moving at speed when cutting.'),
            ('extracut_length', 'The value for extra cnccut over the first point in path,in the job end; float'),
            ('dpp', 'If present then use multidepth cnc cut. Height of one layer for multidepth. Positive value.'),
            ('toolchangez', 'Z distance for toolchange (example: 30.0).\n'
                            'If used in the command then a toolchange event will be included in gcode'),
            ('toolchangexy', 'The X,Y coordinates at Toolchange event in format (x, y) (example: (30.0, 15.2) or '
                             'without parenthesis like: 0.3,1.0). WARNING: no spaces allowed in the value.'),
            ('startz', 'Height before the first move.'),
            ('endz', 'Height where the last move will park.'),
            ('endxy', 'The X,Y coordinates at job end in format (x, y) (example: (2.0, 1.2) or without parenthesis'
                      'like: 0.3,1.0). WARNING: no spaces allowed in the value.'),
            ('spindlespeed', 'Speed of the spindle in rpm (example: 4000).'),
            ('dwelltime', 'Time to pause to allow the spindle to reach the full speed.\n'
                          'If it is not used in command then it will not be included'),
            ('outname', 'Name of the resulting Geometry object.'),
            ('las_power', 'Used with "laser" preprocessors. Set the laser power when cutting'),
            ('las_min_pwr', 'Used with "laser" preprocessors. Set the laser power when not cutting, travelling'),
            ('pp', 'Name of the Geometry preprocessor. No quotes, case sensitive'),
            ('muted', 'It will not put errors in the Shell. Can be True (1) or False (0)')
        ]),
        'examples': ['cncjob geo_name -dia 0.5 -z_cut -1.8 -dpp 0.6 -z_move 2 -feedrate 120 -pp default']
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
            try:
                par = args['muted'].capitalize()
            except AttributeError:
                par = args['muted']
            muted = bool(eval(par))
        else:
            muted = False

        try:
            name = args['name']
        except KeyError:
            if muted is False:
                self.raise_tcl_error("Object name is missing")
                return "fail"
            else:
                return "fail"

        if 'outname' not in args:
            args['outname'] = str(name) + "_cnc"

        obj = self.app.collection.get_by_name(str(name), isCaseSensitive=False)

        if obj is None:
            if muted is False:
                self.raise_tcl_error("Object not found: %s" % str(name))
                return "fail"
            else:
                return "fail"

        if obj.kind != 'geometry':
            if muted is False:
                self.raise_tcl_error('Expected GeometryObject, got %s %s.' % (str(name), type(obj)))
                return "fail"
            else:
                return

        args["dia"] = args["dia"] if "dia" in args and args["dia"] else self.app.defaults["tools_mill_tooldia"]

        args["z_cut"] = args["z_cut"] if "z_cut" in args and args["z_cut"] else self.app.defaults["geometry_cutz"]
        args["z_move"] = args["z_move"] if "z_move" in args and args["z_move"] else \
            self.app.defaults["geometry_travelz"]

        args["pp"] = args["pp"] if "pp" in args and isinstance(args["pp"], str) else \
            self.app.defaults["tools_mill_ppname_g"]

        args["feedrate"] = args["feedrate"] if "feedrate" in args and args["feedrate"] else \
            self.app.defaults["tools_mill_feedrate"]

        if 'laser' in args["pp"] and "feedrate_z" not in args:
            args["feedrate_z"] = args["feedrate"]
        else:
            args["feedrate_z"] = args["feedrate_z"] if "feedrate_z" in args and args["feedrate_z"] else \
                self.app.defaults["tools_mill_feedrate_z"]
        args["feedrate_rapid"] = args["feedrate_rapid"] if "feedrate_rapid" in args and args["feedrate_rapid"] else \
            self.app.defaults["tools_mill_feedrate_rapid"]

        if "extracut_length" in args:
            args["extracut"] = True
            if args["extracut_length"] is None:
                args["extracut_length"] = 0.0
            else:
                args["extracut_length"] = float(args["extracut_length"])
        else:
            args["extracut"] = self.app.defaults["tools_mill_extracut"]
            args["extracut_length"] = self.app.defaults["tools_mill_extracut_length"]

        if "dpp" in args:
            args["multidepth"] = True
            if args["dpp"] is None:
                args["dpp"] = self.app.defaults["tools_mill_depthperpass"]
            else:
                args["dpp"] = float(args["dpp"])
        else:
            args["multidepth"] = self.app.defaults["tools_mill_multidepth"]
            args["dpp"] = self.app.defaults["tools_mill_depthperpass"]

        args["startz"] = args["startz"] if "startz" in args and args["startz"] else \
            self.app.defaults["tools_mill_startz"]
        args["endz"] = args["endz"] if "endz" in args and args["endz"] else self.app.defaults["tools_mill_endz"]

        if "endxy" in args and args["endxy"]:
            args["endxy"] = args["endxy"]
        else:
            if self.app.defaults["tools_mill_endxy"]:
                args["endxy"] = str(self.app.defaults["tools_mill_endxy"])
            else:
                args["endxy"] = '0, 0'
        if len(eval(args["endxy"])) != 2:
            self.raise_tcl_error("The entered value for 'endxy' needs to have the format x,y or "
                                 "in format (x, y) - no spaces allowed. But always two comma separated values.")

        # Spindle speed
        if 'laser' not in args["pp"]:
            args["spindlespeed"] = (args["spindlespeed"] if "spindlespeed" in args and
                                                            args["spindlespeed"] != 0 else None)
        else:
            args["spindlespeed"] = args["las_power"] if "las_power" in args else 0.0

        # Laser minimum power
        args["las_min_pwr"] = args["las_min_pwr"] if "las_min_pwr" in args else 0.0

        if 'dwelltime' in args:
            args["dwell"] = True
            if args['dwelltime'] is None:
                args["dwelltime"] = float(obj.options["dwelltime"])
            else:
                args["dwelltime"] = float(args['dwelltime'])
        else:
            args["dwell"] = self.app.defaults["tools_mill_dwell"]
            args["dwelltime"] = self.app.defaults["tools_mill_dwelltime"]

        if "toolchangez" in args:
            args["toolchange"] = True
            if args["toolchangez"] is not None:
                args["toolchangez"] = args["toolchangez"]
            else:
                args["toolchangez"] = self.app.defaults["tools_mill_toolchangez"]
        else:
            args["toolchange"] = self.app.defaults["tools_mill_toolchange"]
            args["toolchangez"] = self.app.defaults["tools_mill_toolchangez"]

        if "toolchangexy" in args and args["toolchangexy"]:
            args["toolchangexy"] = args["toolchangexy"]
        else:
            if self.app.defaults["tools_mill_toolchangexy"]:
                args["toolchangexy"] = str(self.app.defaults["tools_mill_toolchangexy"])
            else:
                args["toolchangexy"] = '0, 0'
        if len(eval(args["toolchangexy"])) != 2:
            self.raise_tcl_error("The entered value for 'toolchangexy' needs to have the format x,y or "
                                 "in format (x, y) - no spaces allowed. But always two comma separated values.")
            return "fail"

        args.pop('name', None)
        args.pop('las_power', None)
        args.pop('las_min_pwr', None)

        for arg in args:
            if arg == "toolchange_xy" or arg == "spindlespeed" or arg == "startz":
                continue
            else:
                if args[arg] is None:
                    self.app.log.error("None parameters: %s is None" % arg)
                    if muted is False:
                        self.raise_tcl_error('One of the command parameters that have to be not None, is None.\n'
                                             'The parameter that is None is in the default values found in the list \n'
                                             'generated by the TclCommand "list_sys geom". or in the arguments.')
                        return "fail"
                    else:
                        return "fail"

        # HACK !!! Should be solved elsewhere!!!
        # default option for multidepth is False
        # obj.options['multidepth'] = False

        if not obj.multigeo:
            obj.generatecncjob(use_thread=False, plot=False, **args)
        else:
            # Update the local_tools_dict values with the args value
            local_tools_dict = deepcopy(obj.tools)

            for tool_uid in list(local_tools_dict.keys()):
                if 'data' in local_tools_dict[tool_uid]:
                    local_tools_dict[tool_uid]['data']['tools_mill_tooldia'] = args["dia"]
                    local_tools_dict[tool_uid]['data']['tools_mill_cutz'] = args["z_cut"]
                    local_tools_dict[tool_uid]['data']['tools_mill_travelz'] = args["z_move"]
                    local_tools_dict[tool_uid]['data']['tools_mill_feedrate'] = args["feedrate"]
                    local_tools_dict[tool_uid]['data']['tools_mill_feedrate_z'] = args["feedrate_z"]
                    local_tools_dict[tool_uid]['data']['tools_mill_feedrate_rapid'] = args["feedrate_rapid"]
                    local_tools_dict[tool_uid]['data']['tools_mill_multidepth'] = args["multidepth"]
                    local_tools_dict[tool_uid]['data']['tools_mill_extracut'] = args["extracut"]

                    if args["extracut"] is True:
                        local_tools_dict[tool_uid]['data']['tools_mill_extracut_length'] = args["extracut_length"]
                    else:
                        local_tools_dict[tool_uid]['data']['tools_mill_extracut_length'] = None

                    local_tools_dict[tool_uid]['data']['tools_mill_depthperpass'] = args["dpp"]
                    local_tools_dict[tool_uid]['data']['tools_mill_toolchange'] = args["toolchange"]
                    local_tools_dict[tool_uid]['data']['tools_mill_toolchangez'] = args["toolchangez"]
                    local_tools_dict[tool_uid]['data']['tools_mill_toolchangexy'] = args["toolchangexy"]
                    local_tools_dict[tool_uid]['data']['tools_mill_startz'] = args["startz"]
                    local_tools_dict[tool_uid]['data']['tools_mill_endz'] = args["endz"]
                    local_tools_dict[tool_uid]['data']['tools_mill_endxy'] = args["endxy"]
                    local_tools_dict[tool_uid]['data']['tools_mill_spindlespeed'] = args["spindlespeed"]
                    local_tools_dict[tool_uid]['data']['tools_mill_dwell'] = args["dwell"]
                    local_tools_dict[tool_uid]['data']['tools_mill_dwelltime'] = args["dwelltime"]
                    local_tools_dict[tool_uid]['data']['tools_mill_min_power'] = args["las_min_pwr"]
                    local_tools_dict[tool_uid]['data']['tools_mill_ppname_g'] = args["pp"]

            self.app.milling_tool.mtool_gen_cncjob(
                geo_obj=obj,
                outname=args['outname'],
                tools_dict=local_tools_dict,
                tools_in_use=[],
                toolchange=args["toolchange"],
                use_thread=False,
                plot=False,
                from_tcl=True)
            # self.raise_tcl_error('The object is a multi-geo geometry which is not supported in cncjob Tcl Command')
