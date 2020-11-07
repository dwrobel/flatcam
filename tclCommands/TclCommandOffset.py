from tclCommands.TclCommand import TclCommand

import collections


class TclCommandOffset(TclCommand):
    """
    Tcl shell command to change the position of the object.

    example:
        offset my_geometry 1.2 -0.3
    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['offset']

    description = '%s %s' % ("--", "Will offset the geometry of a named object. Does not create a new object.")

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str),
        ('x', float),
        ('y', float)
    ])

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('x', float),
        ('y', float)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Changes the position of the object on X and/or Y axis.",
        'args': collections.OrderedDict([
            ('name', 'Name of the object to offset. Required.'),
            ('x', 'Offset distance in the X axis. If it is not used it will be assumed to be 0.0'),
            ('y', 'Offset distance in the Y axis. If it is not used it will be assumed to be 0.0')
        ]),
        'examples': ['offset my_geometry -x 1.2 -y -0.3', 'offset my_geometry -x 1.0']
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """

        name = args['name']
        off_x = args['x'] if 'x' in args else 0.0
        off_y = args['y'] if 'y' in args else 0.0

        x, y = float(off_x), float(off_y)

        if (x, y) == (0.0, 0.0):
            return

        self.app.collection.get_by_name(name).offset((x, y))
