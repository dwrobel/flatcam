from ObjectCollection import *
import TclCommand


class TclCommandOptions(TclCommand.TclCommandSignaled):
    """
    Tcl shell command to open an Excellon file.
    """

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = ['options']

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
        'main': "Shows the settings for an object.",
        'args': collections.OrderedDict([
            ('name', 'Object name.'),
        ]),
        'examples': []
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
