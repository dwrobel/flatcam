from ObjectCollection import *
from tclCommands.TclCommand import TclCommandSignaled


class TclCommandMillSlots(TclCommandSignaled):
    """
    Tcl shell command to Create Geometry Object for milling holes from Excellon.

    example:
        millholes my_drill -tools 1,2,3 -tooldia 0.1 -outname mill_holes_geo
    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['millslots', 'mills']

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
        ('use_threads', bool)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Create Geometry Object for milling slot holes from Excellon.",
        'args': collections.OrderedDict([
            ('name', 'Name of the Excellon Object.'),
            ('milled_dias', 'Comma separated tool diameters of the slots to be milled (example: 0.6, 1.0 or 3.125).'),
            ('tooldia', 'Diameter of the milling tool (example: 0.1).'),
            ('outname', 'Name of object to create.'),
            ('use_thread', 'If to use multithreading: True or False.')
        ]),
        'examples': ['millholes mydrills']
    }

    def execute(self, args, unnamed_args):
        """

        :param args: array of known named arguments and options
        :param unnamed_args: array of other values which were passed into command
            without -somename and  we do not have them in known arg_names
        :return: None or exception
        """

        name = args['name']

        if 'outname' not in args:
            args['outname'] = name + "_mill_slots"

        try:
            obj = self.app.collection.get_by_name(str(name))
        except:
            obj = None
            self.raise_tcl_error("Could not retrieve object: %s" % name)

        if not obj.slots:
            self.raise_tcl_error("The Excellon object has no slots: %s" % name)

        try:
            if 'milled_dias' in args and args['milled_dias'] != 'all':
                diameters = [x.strip() for x in args['tools'].split(",")]
                req_tools = []
                for tool in obj.tools:
                    for req_dia in diameters:
                        if float('%.4f' % float(obj.tools[tool]["C"])) == float('%.4f' % float(req_dia)):
                            req_tools.append(tool)

                args['tools'] = req_tools

                # no longer needed
                del args['milled_dias']

                # Split and put back. We are passing the whole dictionary later.
                # args['milled_dias'] = [x.strip() for x in args['tools'].split(",")]
            else:
                args['tools'] = 'all'
        except Exception as e:
            self.raise_tcl_error("Bad tools: %s" % str(e))

        if not isinstance(obj, FlatCAMExcellon):
            self.raise_tcl_error('Only Excellon objects can have mill-slots, got %s %s.' % (name, type(obj)))

        if self.app.collection.has_promises():
            self.raise_tcl_error('!!!Promises exists, but should not here!!!')

        try:
            # 'name' is not an argument of obj.generate_milling()
            del args['name']

            # This runs in the background... Is blocking handled?
            success, msg = obj.generate_milling_slots(**args)

        except Exception as e:
            success = None
            msg = None
            self.raise_tcl_error("Operation failed: %s" % str(e))

        if not success:
            self.raise_tcl_error(msg)
