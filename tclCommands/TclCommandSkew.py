from ObjectCollection import *
from tclCommands.TclCommand import TclCommand


class TclCommandSkew(TclCommand):
    """
    Tcl shell command to skew the object by a an angle over X axis and an angle over Y axes.

    example:
        skew my_geometry 10.2 3.5
    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['skew']

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str),
        ('angle_x', float),
        ('angle_y', float)
    ])

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([

    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name', 'angle_x', 'angle_y']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Shear/Skew an object by angles along x and y dimensions. The reference point is the left corner of "
                "the bounding box of the object.",
        'args': collections.OrderedDict([
            ('name', 'Name of the object to skew.'),
            ('angle_x', 'Angle in degrees by which to skew on the X axis.'),
            ('angle_y', 'Angle in degrees by which to skew on the Y axis.')
        ]),
        'examples': ['skew my_geometry 10.2 3.5']
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """

        name = args['name']
        angle_x = float(args['angle_x'])
        angle_y = float(args['angle_y'])

        obj_to_skew = self.app.collection.get_by_name(name)
        xmin, ymin, xmax, ymax = obj_to_skew.bounds()
        obj_to_skew.skew(angle_x, angle_y, point=(xmin, ymin))
