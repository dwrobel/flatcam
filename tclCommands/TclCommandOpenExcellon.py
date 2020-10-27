from tclCommands.TclCommand import TclCommandSignaled

import collections


class TclCommandOpenExcellon(TclCommandSignaled):
    """
    Tcl shell command to open an Excellon file.
    """

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = ['open_excellon']

    description = '%s %s' % ("--", "Opens an Excellon file, parse it and create a Excellon object from it.")

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
        'main': "Opens an Excellon file, parse it and create a Excellon object from it.",
        'args': collections.OrderedDict([
            ('filename', 'Absolute path to file to open. Required.\n'
                         'WARNING: no spaces are allowed. If unsure enclose the entire path with quotes.'),
            ('outname', 'Name of the resulting Excellon object.')
        ]),
        'examples': ['open_excellon D:\\my_excellon_file.DRL',
                     'open_excellon "D:\\my_excellon_file with spaces in the name.DRL"',
                     'open_excellon path_to_file']
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

        # if ' ' in filename:
        #     return "The absolute path to the project file contain spaces which is not allowed.\n" \
        #            "Please enclose the path within quotes."

        args['plot'] = False
        args['from_tcl'] = True
        self.app.f_handlers.open_excellon(filename, **args)
