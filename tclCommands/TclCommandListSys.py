from tclCommands.TclCommand import *


class TclCommandListSys(TclCommand):
    """
    Tcl shell command to get the list of system variables

    example:
        list_sys
    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['list_sys', 'listsys']

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
    ])

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([

    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = []

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Returns the list of the names of system variables.\n"
                "Note: Use get_sys command to get the value and set_sys command to set it.",
        'args': collections.OrderedDict([
        ]),
        'examples': []
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """
        return str([*self.app.defaults])