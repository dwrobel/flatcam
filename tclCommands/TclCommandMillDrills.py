# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 8/17/2019                                          #
# MIT Licence                                              #
# ##########################################################

from tclCommands.TclCommand import TclCommandSignaled

import math
import collections


class TclCommandMillDrills(TclCommandSignaled):
    """
    Tcl shell command to Create Geometry Object for milling holes from Excellon.

    example:
        millholes my_drill -tools 1,2,3 -tooldia 0.1 -outname mill_holes_geo
    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['milldrills', 'milld']

    description = '%s %s' % ("--", "Create a Geometry Object for milling drill holes from Excellon.")

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str)
    ])

    # Dictionary of types from Tcl command, needs to be ordered.
    # This is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('milled_dias', str),
        ('outname', str),
        ('tooldia', float),
        ('use_thread', str),
        ('diatol', float)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Create a Geometry Object for milling drill holes from Excellon.",
        'args': collections.OrderedDict([
            ('name', 'Name of the Excellon Object. Required.'),
            ('milled_dias', 'Comma separated tool diameters of the drills to be milled (example: 0.6, 1.0 or 3.125).\n'
                            'Exception: if you enter "all" then the drills for all tools will be milled.\n'
                            'WARNING: no spaces are allowed in the list of tools.\n'
                            'As a precaution you can enclose them with quotes.'),
            ('tooldia', 'Diameter of the milling tool (example: 0.1).'),
            ('outname', 'Name of Geometry object to be created holding the milled geometries.'),
            ('use_thread', 'If to use multithreading: True (1) or False (0).'),
            ('diatol', 'Tolerance. Percentange (0.0 ... 100.0) within which dias in milled_dias will be judged to be '
                       'the same as the ones in the tools from the Excellon object. E.g: if in milled_dias we have a '
                       'diameter with value 1.0, in the Excellon we have a tool with dia = 1.05 and we set a tolerance '
                       'diatol = 5.0 then the drills with the dia = (0.95 ... 1.05) '
                       'in Excellon will be processed. Float number.')
        ]),
        'examples': ['milldrills mydrills -milled_dias "0.6,0.8" -tooldia 0.1 -diatol 10 -outname milled_holes',
                     'milld my_excellon.drl']
    }

    def execute(self, args, unnamed_args):
        """

        :param args: array of known named arguments and options
        :param unnamed_args: array of other values which were passed into command
            without -somename and  we do not have them in known arg_names
        :return: None or exception
        """

        name = args['name']

        try:
            obj = self.app.collection.get_by_name(str(name))
        except Exception:
            obj = None
            self.raise_tcl_error("Could not retrieve object: %s" % name)

        if 'outname' not in args:
            args['outname'] = name + "_mill_drills"

        if 'use_thread' in args:
            try:
                par = args['use_thread'].capitalize()
            except AttributeError:
                par = args['use_thread']
            args['use_thread'] = bool(eval(par))
        else:
            args['use_thread'] = False

        if not obj.drills:
            self.raise_tcl_error("The Excellon object has no drills: %s" % name)

        try:
            if 'milled_dias' in args and args['milled_dias'] != 'all':
                diameters = [x.strip() for x in args['milled_dias'].split(",") if x != '']
                nr_diameters = len(diameters)

                req_tools = set()
                for tool in obj.tools:
                    for req_dia in diameters:
                        obj_dia_form = float('%.*f' % (obj.decimals, float(obj.tools[tool]["C"])))
                        req_dia_form = float('%.*f' % (obj.decimals, float(req_dia)))

                        if 'diatol' in args:
                            tolerance = float(args['diatol']) / 100

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
                    self.raise_tcl_error("One or more tool diameters of the drills to be milled passed to the "
                                         "TclCommand are not actual tool diameters in the Excellon object.")

                args['tools'] = req_tools

                # no longer needed
                del args['milled_dias']
                del args['diatol']

                # Split and put back. We are passing the whole dictionary later.
                # args['milled_dias'] = [x.strip() for x in args['tools'].split(",")]
            else:
                args['tools'] = 'all'
        except Exception as e:
            self.raise_tcl_error("Bad tools: %s" % str(e))

        if obj.kind != 'excellon':
            self.raise_tcl_error('Only Excellon objects can be mill-drilled, got %s %s.' % (name, type(obj)))

        if self.app.collection.has_promises():
            self.raise_tcl_error('!!!Promises exists, but should not here!!!')

        try:
            # 'name' is not an argument of obj.generate_milling()
            del args['name']

            # This runs in the background... Is blocking handled?
            success, msg = obj.generate_milling_drills(plot=False, **args)
        except Exception as e:
            success = None
            msg = None
            self.raise_tcl_error("Operation failed: %s" % str(e))

        if not success:
            self.raise_tcl_error(msg)
