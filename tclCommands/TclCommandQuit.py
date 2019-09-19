from ObjectCollection import *
from tclCommands.TclCommand import TclCommand


class TclCommandQuit(TclCommand):
    """
    Tcl shell command to quit FlatCAM from Tcl shell.

    example:

    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['quit_flatcam']

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
        'main': "Tcl shell command to quit FlatCAM from Tcl shell.",
        'args': collections.OrderedDict([

        ]),
        'examples': ['quit_flatcam']
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """

        self.app.quit_application()

