from tclCommands.TclCommand import TclCommandSignaled

import collections


class TclCommandNewGeometry(TclCommandSignaled):
    """
    Tcl shell command to subtract polygon from the given Geometry object.
    """

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = ['new_geometry']

    description = '%s %s' % ("--", "Creates a new empty Geometry object.")

    # Dictionary of types from Tcl command, needs to be ordered.
    # For positional arguments
    arg_names = collections.OrderedDict([
        ('name', str)
    ])

    # Dictionary of types from Tcl command, needs to be ordered.
    # For options like -optionname value
    option_types = collections.OrderedDict([

    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = []

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Creates a new empty Geometry object.",
        'args': collections.OrderedDict([
            ('name', 'New object name.'),
        ]),
        'examples': ['new_geometry\n'
                     'new_geometry my_new_geo']
    }

    def execute(self, args, unnamed_args):
        """
        execute current TCL shell command

        :param args: array of known named arguments and options
        :param unnamed_args: array of other values which were passed into command
            without -somename and  we do not have them in known arg_names
        :return: None or exception
        """
        if 'name' in args:
            name = args['name']
        else:
            name = 'new_geo'

        self.app.app_obj.new_object('geometry', str(name), lambda x, y: None, plot=False)
