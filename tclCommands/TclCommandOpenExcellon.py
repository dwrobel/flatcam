from tclCommands.TclCommand import *


class TclCommandOpenExcellon(TclCommandSignaled):
    """
    Tcl shell command to open an Excellon file.
    """

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = ['open_excellon']

    # Dictionary of types from Tcl command, needs to be ordered.
    # For positional arguments
    arg_names = collections.OrderedDict([
        ('filename', str)
    ])

    # Dictionary of types from Tcl command, needs to be ordered.
    # For options like -optionname value
    option_types = collections.OrderedDict([
        ('outname', str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['filename']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Opens an Excellon file.",
        'args': collections.OrderedDict([
            ('filename', 'Path to file to open.'),
            ('outname', 'Name of the resulting Excellon object.')
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

        filename = args.pop('filename')

        self.app.open_excellon(filename, **args)
