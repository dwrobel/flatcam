from tclCommands.TclCommand import *


class TclCommandMillHoles(TclCommandSignaled):
    """
    Tcl shell command to Create Geometry Object for milling holes from Excellon.

    example:
        millholes my_drill -tools 1,2,3 -tooldia 0.1 -outname mill_holes_geo
    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['millholes']

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str)
    ])

    # Dictionary of types from Tcl command, needs to be ordered.
    # This is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('tools', str),
        ('outname', str),
        ('tooldia', float)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Create Geometry Object for milling holes from Excellon.",
        'args': collections.OrderedDict([
            ('name', 'Name of the Excellon Object.'),
            ('tools', 'Comma separated indexes of tools (example: 1,3 or 2).'),
            ('tooldia', 'Diameter of the milling tool (example: 0.1).'),
            ('outname', 'Name of object to create.')
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
            args['outname'] = name + "_mill"

        try:
            if 'tools' in args and args['tools'] != 'all':
                # Split and put back. We are passing the whole dictionary later.
                args['tools'] = [x.strip() for x in args['tools'].split(",")]
            else:
                args['tools'] = 'all'
        except Exception as e:
            self.raise_tcl_error("Bad tools: %s" % str(e))

        try:
            obj = self.app.collection.get_by_name(str(name))
        except:
            self.raise_tcl_error("Could not retrieve object: %s" % name)

        if not isinstance(obj, FlatCAMExcellon):
            self.raise_tcl_error('Only Excellon objects can be mill-drilled, got %s %s.' % (name, type(obj)))

        try:
            # 'name' is not an argument of obj.generate_milling()
            del args['name']

            # This runs in the background... Is blocking handled?
            success, msg = obj.generate_milling(**args)

        except Exception as e:
            self.raise_tcl_error("Operation failed: %s" % str(e))

        if not success:
            self.raise_tcl_error(msg)
