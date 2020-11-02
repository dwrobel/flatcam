# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 4/28/2020                                          #
# MIT Licence                                              #
# ##########################################################

from tclCommands.TclCommand import TclCommand

import collections
import logging
import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class TclCommandGetPath(TclCommand):
    """
    Tcl shell command to get the current default path set for Tcl.

    example:

    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['get_path']

    description = '%s %s' % ("--", "Get the default Tcl Shell folder path.")

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
        'main': "Will get the folder path used as a fallback path for opening files.",
        'args': collections.OrderedDict([
        ]),
        'examples': ['get_path']
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """

        self.app.shell.append_output("Current default Tcl Shell path is: ")
        path = self.app.defaults["global_tcl_path"]
        return path
