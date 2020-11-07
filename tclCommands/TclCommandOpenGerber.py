from tclCommands.TclCommand import TclCommandSignaled
from camlib import ParseError

import collections


class TclCommandOpenGerber(TclCommandSignaled):
    """
    Tcl shell command to opens a Gerber file
    """

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = ['open_gerber']

    description = '%s %s' % ("--", "Opens an Gerber file, parse it and create a Gerber object from it.")

    # dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('filename', str)
    ])

    # dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('outname', str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['filename']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Opens a Gerber file.",
        'args': collections.OrderedDict([
            ('filename', 'Absolute path to file to open. Required.\n'
                         'WARNING: no spaces are allowed. If unsure enclose the entire path with quotes.'),
            ('outname', 'Name of the resulting Gerber object.')
        ]),
        'examples': ["open_gerber gerber_object_path -outname bla",
                     'open_gerber "D:\\my_gerber_file with spaces in the name.GRB"']
    }

    def execute(self, args, unnamed_args):
        """
        execute current TCL shell command

        :param args: array of known named arguments and options
        :param unnamed_args: array of other values which were passed into command
            without -somename and  we do not have them in known arg_names
        :return: None or exception
        """

        if 'follow' in args:
            self.raise_tcl_error("The 'follow' parameter is obsolete. To create 'follow' geometry use the 'follow' "
                                 "parameter for the Tcl Command isolate()")

        filename = args.pop('filename')

        if 'outname' in args:
            outname = args.pop('outname')
        else:
            outname = filename.split('/')[-1].split('\\')[-1]

        args['plot'] = False
        args['from_tcl'] = True
        self.app.f_handlers.open_gerber(filename, outname, **args)
