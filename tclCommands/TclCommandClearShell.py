# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 8/17/2019                                          #
# MIT Licence                                              #
# ##########################################################

from tclCommands.TclCommand import TclCommand
import collections


class TclCommandClearShell(TclCommand):
    """
    Tcl shell command to clear the text in the Tcl Shell browser.

    example:

    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['clear']

    description = '%s %s' % ("--", "Clear the text in the Tcl Shell.")

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
        'main': "Clear the text in the Tcl Shell.",
        'args': collections.OrderedDict([
        ]),
        'examples': ['clear']
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """
        self.app.inform.emit("Tcl Shell Editor cleared ...")
        self.app.shell._browser.clear()
        pass
