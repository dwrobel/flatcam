from tclCommands.TclCommand import TclCommandSignaled

import collections


class TclCommandSaveProject(TclCommandSignaled):
    """
    Tcl shell command to save the FlatCAM project to file.
    """

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = ['save_project']

    description = '%s %s' % ("--", "Saves the FlatCAM project to file.")

    # Dictionary of types from Tcl command, needs to be ordered.
    # For positional arguments
    arg_names = collections.OrderedDict([
        ('filename', str)
    ])

    # Dictionary of types from Tcl command, needs to be ordered.
    # For options like -optionname value
    option_types = collections.OrderedDict([

    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['filename']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Saves the FlatCAM project to file.",
        'args': collections.OrderedDict([
            ('filename', 'Absolute path to file to save. Required.\n'
                         'WARNING: no spaces are allowed. If unsure enclose the entire path with quotes.'),
        ]),
        'examples': ['save_project D:\\my_project_file.FlatPrj',
                     'save_project "D:\\my_project_file with spaces in the name.FlatPrj"',
                     'save_project path_to_where_the_file_is_stored']
    }

    def execute(self, args, unnamed_args):
        """
        execute current TCL shell command

        :param args: array of known named arguments and options
        :param unnamed_args: array of other values which were passed into command
            without -somename and  we do not have them in known arg_names
        :return: None or exception
        """

        self.app.save_project(args['filename'], from_tcl=True)
