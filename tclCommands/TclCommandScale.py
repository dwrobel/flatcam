from ObjectCollection import *
from tclCommands.TclCommand import TclCommand


class TclCommandScale(TclCommand):
    """
    Tcl shell command to resizes the object by a factor.

    example:
        scale my_geometry 4.2
    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['scale']

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str),
        ('factor', float)
    ])

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([

    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name', 'factor']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Resizes the object by a factor.",
        'args': collections.OrderedDict([
            ('name', 'Name of the object to resize.'),
            ('factor', 'Fraction by which to scale.')
        ]),
        'examples': ['scale my_geometry 4.2']
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """

        name = args['name']
        factor = args['factor']

        self.app.collection.get_by_name(name).scale(factor)
