from ObjectCollection import *
from tclCommands.TclCommand import TclCommand


class TclCommandGetNames(TclCommand):
    """
    Tcl shell command to set an object as active in the GUI.

    example:

    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['get_names']

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
        'main': 'Lists the names of objects in the project.',
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

        return '\n'.join(self.app.collection.get_names())
