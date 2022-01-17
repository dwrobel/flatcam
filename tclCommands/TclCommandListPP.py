# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 1/18/2022                                         #
# MIT Licence                                              #
# ##########################################################

from tclCommands.TclCommand import *


class TclCommandListPP(TclCommand):
    """
    Tcl shell command to get the list of available preprocessors

    example:
        list_pp
    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['list_pp', 'listpp']

    description = '%s %s' % ("--", "Outputs in Tcl Shell the list with the names of available preprocessors.")

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
        'main': "Returns the list with the names of available preprocessors.\n",
        'args': collections.OrderedDict([
        ]),
        'examples': ['list_pp', 'listpp']
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """
        ret_val = list(self.app.preprocessors.keys())
        return str(ret_val)
