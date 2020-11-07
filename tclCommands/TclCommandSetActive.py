from tclCommands.TclCommand import TclCommand

import collections


class TclCommandSetActive(TclCommand):
    """
    Tcl shell command to set an object as active in the appGUI.

    example:

    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['set_active']

    description = '%s %s' % ("--", "Sets a FlatCAM object as active (selected).")

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str),
    ])

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([

    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': 'Sets a FlatCAM object as active (selected).',
        'args': collections.OrderedDict([
            ('name', 'Name of the FlatCAM object to be set as active (selected). Required.'),
        ]),
        'examples': ['set_active object_name']
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """

        obj_name = args['name']

        try:
            self.app.collection.set_active(str(obj_name))
        except Exception as e:
            return "Command failed: %s" % str(e)
