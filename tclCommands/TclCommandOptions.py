from tclCommands.TclCommand import TclCommandSignaled

import collections


class TclCommandOptions(TclCommandSignaled):
    """
    Tcl shell command to open an Excellon file.
    """

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = ['options']

    description = '%s %s' % ("--", "Will return the options (settings) for an object as a string "
                                   "with values separated by \\n.")

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
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Will return the options (settings) for an object as a string with values separated by \\n.",
        'args': collections.OrderedDict([
            ('name', 'Object name for which to return the options. Required.'),
        ]),
        'examples': ['options obj_name']
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

        ops = self.app.collection.get_by_name(str(name)).options
        return '\n'.join(["%s: %s" % (o, ops[o]) for o in ops])
