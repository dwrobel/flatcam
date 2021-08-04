from tclCommands.TclCommand import *
from PyQt6.QtWidgets import QFileDialog


class TclCommandOpenFolder(TclCommand):
    """
    Tcl shell command to get open a folder browser dialog and return the result

    example:
        open_folder
    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['open_folder']

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict()

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('dir', str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = []

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Opens a dialog to browse for a folder",
        'args': collections.OrderedDict([
            ('dir', 'Initial directory to open')
        ]),
        'examples': ['open_folder']
    }

    def execute(self, args, unnamed_args):
        """
        execute current TCL shell command

        :param args: array of known named arguments and options
        :param unnamed_args: array of other values which were passed into command
            without -somename and  we do not have them in known arg_names
        :return: None or exception
        """
        if "dir" in args:
            return QFileDialog.getExistingDirectory(dir=args['dir'])
        else:
            return QFileDialog.getExistingDirectory()
