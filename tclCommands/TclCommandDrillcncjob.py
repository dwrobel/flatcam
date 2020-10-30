from tclCommands.TclCommand import TclCommandSignaled

import collections
import math

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class TclCommandDrillcncjob(TclCommandSignaled):
    """
    Tcl shell command to Generates a Drill CNC Job from a Excellon Object.
    """

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = ['drillcncjob']

    description = '%s %s' % ("--", "Generates a Drill CNC Job object from a Excellon Object.")

    # dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str)
    ])

    # dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('drilled_dias', str),
        ('drillz', float),
        ('dpp', float),
        ('travelz', float),
        ('feedrate_z', float),
        ('feedrate_rapid', float),
        ('spindlespeed', int),
        ('toolchangez', float),
        ('toolchangexy', str),
        ('startz', float),
        ('endz', float),
        ('endxy', str),
        ('dwelltime', float),
        ('pp', str),
        ('opt_type', str),
        ('diatol', float),
        ('muted', str),
        ('outname', str)
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
             'WARNING: No space allowed'),
            ('drillz', 'Drill depth into material (example: -2.0). Negative value.'),
            ('dpp', 'Progressive drilling into material with a specified step (example: 0.7). Positive value.'),
            ('travelz', 'Travel distance above material (example: 2.0).'),
            ('feedrate_z', 'Drilling feed rate. It is the speed on the Z axis.'),
            ('feedrate_rapid', 'Rapid drilling feed rate.'),
            ('spindlespeed', 'Speed of the spindle in rpm (example: 4000).'),
            ('toolchangez', 'Z distance for toolchange (example: 30.0).\n'
                            'If used in the command then a toolchange event will be included in gcode'),
            ('toolchangexy', 'The X,Y coordinates at Toolchange event in format (x, y) (example: (30.0, 15.2) or '
                             'without parenthesis like: 0.3,1.0). WARNING: no spaces allowed in the value.'),
            ('startz', 'The Z coordinate at job start (example: 30.0).'),
            ('endz', 'The Z coordinate at job end (example: 30.0).'),
            ('endxy', 'The X,Y coordinates at job end in format (x, y) (example: (2.0, 1.2) or without parenthesis'
                      'like: 0.3,1.0). WARNING: no spaces allowed in the value.'),
            ('dwelltime', 'Time to pause to allow the spindle to reach the full speed.\n'
                          'If it is not used in command then it will not be included'),
            ('pp', 'This is the Excellon preprocessor name: case_sensitive, no_quotes'),
            ('opt_type', 'Name of move optimization type. B by default for Basic OR-Tools, M for Metaheuristic OR-Tools'
                         'T from Travelling Salesman Algorithm. B and M works only for 64bit version of FlatCAM and '
                         'T works only for 32bit version of FlatCAM'),
            ('diatol', 'Tolerance. Percentange (0.0 ... 100.0) within which dias in drilled_dias will be judged to be '
                       'the same as the ones in the tools from the Excellon object. E.g: if in drill_dias we have a '
                       'diameter with value 1.0, in the Excellon we have a tool with dia = 1.05 and we set a tolerance '
                       'diatol = 5.0 then the drills with the dia = (0.95 ... 1.05) '
                       'in Excellon will be processed. Float number.'),
            ('muted', 'It will not put errors in the Shell or status bar. Can be True (1) or False (0).'),
            ('outname', 'Name of the resulting Geometry object.')
        ]),
        'examples': ['drillcncjob test.TXT -drillz -1.5 -travelz 14 -feedrate_z 222 -feedrate_rapid 456 '
                     '-spindlespeed 777 -toolchangez 33 -endz 22 -pp default\n'
                     'Usage of -feedrate_rapid matter only when the preprocessor is using it, like -marlin-.',
                     'drillcncjob test.DRL -drillz -1.7 -dpp 0.5 -travelz 2 -feedrate_z 800 -endxy 3,3']
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
            try:
                par = args['muted'].capitalize()
            except AttributeError:
                par = args['muted']
            muted = bool(eval(par))
        else:
            muted = False

        if obj is None:
            if muted is False:
                self.raise_tcl_error("Object not found: %s" % name)
            else:
                return "fail"

        if obj.kind != 'excellon':
            if muted is False:
                self.raise_tcl_error('Expected ExcellonObject, got %s %s.' % (name, type(obj)))
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
                        if muted is False:
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

                if muted is False:
                    self.raise_tcl_error("Bad tools: %s" % str(e))
                else:
                    return "fail"

            used_tools_info = []
            used_tools_info.insert(0, [_("Tool_nr"), _("Diameter"), _("Drills_Nr"), _("Slots_Nr")])

            # populate the information's list for used tools
            if tools == 'all':
                sort = []
                for k, v in list(obj.tools.items()):
                    sort.append((k, v.get('tooldia')))
                sorted_tools = sorted(sort, key=lambda t1: t1[1])
                use_tools = [i[0] for i in sorted_tools]

                for tool_no in use_tools:
                    tool_dia_used = obj.tools[tool_no]['tooldia']

                    drill_cnt = 0  # variable to store the nr of drills per tool
                    slot_cnt = 0  # variable to store the nr of slots per tool

                    # Find no of drills for the current tool
                    if 'drills' in obj.tools[tool_no] and obj.tools[tool_no]['drills']:
                        drill_cnt = len(obj.tools[tool_no]['drills'])

                    # Find no of slots for the current tool
                    if 'slots' in obj.tools[tool_no] and obj.tools[tool_no]['slots']:
                        slot_cnt = len(obj.tools[tool_no]['slots'])

                    used_tools_info.append([str(tool_no), str(tool_dia_used), str(drill_cnt), str(slot_cnt)])

            drillz = args["drillz"] if "drillz" in args and args["drillz"] is not None else \
                obj.options["tools_drill_cutz"]

            if "toolchangez" in args:
                toolchange = True
                if args["toolchangez"] is not None:
                    toolchangez = args["toolchangez"]
                else:
                    toolchangez = obj.options["tools_drill_toolchangez"]
            else:
                toolchange = self.app.defaults["tools_drill_toolchange"]
                toolchangez = float(self.app.defaults["tools_drill_toolchangez"])

            if "toolchangexy" in args and args["tools_drill_toolchangexy"]:
                xy_toolchange = args["toolchangexy"]
            else:
                if self.app.defaults["tools_drill_toolchangexy"]:
                    xy_toolchange = str(self.app.defaults["tools_drill_toolchangexy"])
                else:
                    xy_toolchange = '0, 0'
            if len(eval(xy_toolchange)) != 2:
                self.raise_tcl_error("The entered value for 'toolchangexy' needs to have the format x,y or "
                                     "in format (x, y) - no spaces allowed. But always two comma separated values.")

            endz = args["endz"] if "endz" in args and args["endz"] is not None else \
                self.app.defaults["tools_drill_endz"]

            if "endxy" in args and args["endxy"]:
                xy_end = args["endxy"]
            else:
                if self.app.defaults["tools_drill_endxy"]:
                    xy_end = str(self.app.defaults["tools_drill_endxy"])
                else:
                    xy_end = '0, 0'

            if len(eval(xy_end)) != 2:
                self.raise_tcl_error("The entered value for 'xy_end' needs to have the format x,y or "
                                     "in format (x, y) - no spaces allowed. But always two comma separated values.")

            opt_type = args["opt_type"] if "opt_type" in args and args["opt_type"] else 'B'

            # ##########################################################################################
            # ################# Set parameters #########################################################
            # ##########################################################################################
            job_obj.origin_kind = 'excellon'

            job_obj.options['Tools_in_use'] = used_tools_info
            job_obj.options['type'] = 'Excellon'

            pp_excellon_name = args["pp"] if "pp" in args and args["pp"] else self.app.defaults["tools_drill_ppname_e"]
            job_obj.pp_excellon_name = pp_excellon_name
            job_obj.options['ppname_e'] = pp_excellon_name

            if 'dpp' in args:
                job_obj.multidepth = True
                if args['dpp'] is not None:
                    job_obj.z_depthpercut = float(args['dpp'])
                else:
                    job_obj.z_depthpercut = float(obj.options["dpp"])
            else:
                job_obj.multidepth = self.app.defaults["tools_drill_multidepth"]
                job_obj.z_depthpercut = self.app.defaults["tools_drill_depthperpass"]

            job_obj.z_move = float(args["travelz"]) if "travelz" in args and args["travelz"] else \
                self.app.defaults["tools_drill_travelz"]

            job_obj.feedrate = float(args["feedrate_z"]) if "feedrate_z" in args and args["feedrate_z"] else \
                self.app.defaults["tools_drill_feedrate_z"]
            job_obj.z_feedrate = float(args["feedrate_z"]) if "feedrate_z" in args and args["feedrate_z"] else \
                self.app.defaults["tools_drill_feedrate_z"]

            job_obj.feedrate_rapid = float(args["feedrate_rapid"]) \
                if "feedrate_rapid" in args and args["feedrate_rapid"] else \
                self.app.defaults["tools_drill_feedrate_rapid"]

            job_obj.spindlespeed = float(args["spindlespeed"]) if "spindlespeed" in args else None
            job_obj.spindledir = self.app.defaults['tools_drill_spindlespeed']
            if 'dwelltime' in args:
                job_obj.dwell = True
                if args['dwelltime'] is not None:
                    job_obj.dwelltime = float(args['dwelltime'])
                else:
                    job_obj.dwelltime = float(self.app.defaults["tools_drill_dwelltime"])
            else:
                job_obj.dwell = self.app.defaults["tools_drill_dwell"]
                job_obj.dwelltime = self.app.defaults["tools_drill_dwelltime"]

            job_obj.toolchange_xy_type = "excellon"
            job_obj.coords_decimals = int(self.app.defaults["cncjob_coords_decimals"])
            job_obj.fr_decimals = int(self.app.defaults["cncjob_fr_decimals"])

            job_obj.options['xmin'] = xmin
            job_obj.options['ymin'] = ymin
            job_obj.options['xmax'] = xmax
            job_obj.options['ymax'] = ymax

            job_obj.z_cut = float(drillz)
            job_obj.toolchange = toolchange
            job_obj.xy_toolchange = xy_toolchange
            job_obj.z_toolchange = float(toolchangez)

            if "startz" in args and args["startz"] is not None:
                job_obj.startz = float(args["startz"])
            else:
                if self.app.defaults["tools_drill_startz"]:
                    job_obj.startz = self.app.defaults["tools_drill_startz"]
                else:
                    job_obj.startz = self.app.defaults["tools_drill_travelz"]

            job_obj.endz = float(endz)
            job_obj.xy_end = xy_end
            job_obj.excellon_optimization_type = opt_type
            job_obj.spindledir = self.app.defaults["tools_drill_spindledir"]

            ret_val = job_obj.generate_from_excellon_by_tool(obj, tools, use_ui=False)
            job_obj.source_file = ret_val

            if ret_val == 'fail':
                return 'fail'
            job_obj.gc_start = ret_val[1]

            for t_item in job_obj.exc_cnc_tools:
                job_obj.exc_cnc_tools[t_item]['data']['tools_drill_offset'] = \
                    float(job_obj.exc_cnc_tools[t_item]['offset_z']) + float(drillz)
                job_obj.exc_cnc_tools[t_item]['data']['tools_drill_ppname_e'] = job_obj.options['ppname_e']

            job_obj.gcode_parse()
            job_obj.create_geometry()

        self.app.app_obj.new_object("cncjob", args['outname'], job_init, plot=False)
