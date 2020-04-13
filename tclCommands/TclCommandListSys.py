# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 8/17/2019                                          #
# MIT Licence                                              #
# ##########################################################

from tclCommands.TclCommand import *


class TclCommandListSys(TclCommand):
    """
    Tcl shell command to get the list of system variables

    example:
        list_sys
    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['list_sys', 'listsys']

    description = '%s %s' % ("--", "Outputs in Tcl Shell the list with the names of system variables.")

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('selection', str),
    ])

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([

    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = []

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Returns the list of the names of system variables.\n"
                "Without an argument it will list all the system parameters. "
                "As an argument use first letter or first letters from the name "
                "of the system variable.\n"
                "In that case it will list only the system variables that starts with that string.\n"
                "Main categories start with: gerber or excellon or geometry or cncjob or global.\n"
                "Note: Use 'get_sys system variable' to get the value and 'set_sys system variable value' to set it.\n",
        'args': collections.OrderedDict([
        ]),
        'examples': ['list_sys',
                     'list_sys ser',
                     'list_sys gerber',
                     'list_sys cncj']
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """
        if 'selection' in args:
            argument = args['selection']
            return str([k for k in self.app.defaults.keys() if str(k).startswith(str(argument))])
        else:
            ret_val = list(self.app.defaults.keys())
            return str(ret_val)
            # return str([*self.app.defaults])
