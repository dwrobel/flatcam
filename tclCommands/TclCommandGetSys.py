# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 8/17/2019                                          #
# MIT Licence                                              #
# ##########################################################

from tclCommands.TclCommand import TclCommand

import collections


class TclCommandGetSys(TclCommand):
    """
    Tcl shell command to get the value of a system variable

    example:
        get_sys excellon_zeros
    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['get_sys', 'getsys']

    description = '%s %s' % ("--", "Returns to TCL the value for the entered system variable.")

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str)
    ])

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([

    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Returns to TCL the value for the entered system variable.",
        'args': collections.OrderedDict([
            ('name', 'Name of the system variable. Required.'),
        ]),
        'examples': ['get_sys excellon_zeros']
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """

        name = args['name']

        if name in self.app.defaults:
            return self.app.defaults[name]
        else:
            return "The keyword: %s does not exist as a parameter" % str(name)
