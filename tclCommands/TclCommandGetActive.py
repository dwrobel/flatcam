
from tclCommands.TclCommand import TclCommand

import collections


class TclCommandGetActive(TclCommand):
    """
    Tcl shell command to get the current active object name.

    example:

    """

    # List of all command aliases, to be able to use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['get_active']

    description = '%s %s' % ("--", "Gets the active (selected) application object name.")

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
        'main': 'Gets the active (selected) application object name.',
        'args': collections.OrderedDict([
        ]),
        'examples': ['get_active']
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """

        try:
            return self.app.collection.get_active().options['name']
        except Exception as e:
            return "Command failed: %s" % str(e)
