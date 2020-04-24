from tclCommands.TclCommand import TclCommand

import collections


class TclCommandSkew(TclCommand):
    """
    Tcl shell command to skew the object by a an angle over X axis and an angle over Y axes.

    example:
        skew my_geometry 10.2 3.5
    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['skew']

    description = '%s %s' % ("--", "Will deform (skew) the geometry of a named object. Does not create a new object.")

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str),
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
        'main': "Shear/Skew an object along x and y dimensions. The reference point is the left corner of "
                "the bounding box of the object.",
        'args': collections.OrderedDict([
            ('name', 'Name of the object (Gerber, Geometry or Excellon) to be deformed (skewed). Required.'),
            ('x', 'Angle in degrees by which to skew on the X axis. If it is not used it will be assumed to be 0.0'),
            ('y', 'Angle in degrees by which to skew on the Y axis. If it is not used it will be assumed to be 0.0')
        ]),
        'examples': ['skew my_geometry -x 10.2 -y 3.5', 'skew my_geo -x 3.0']
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """

        name = args['name']

        if 'x' in args:
            angle_x = float(args['x'])
        else:
            angle_x = 0.0

        if 'y' in args:
            angle_y = float(args['y'])
        else:
            angle_y = 0.0

        if angle_x == 0.0 and angle_y == 0.0:
            # nothing to be done
            return

        obj_to_skew = self.app.collection.get_by_name(name)
        xmin, ymin, xmax, ymax = obj_to_skew.bounds()
        obj_to_skew.skew(angle_x, angle_y, point=(xmin, ymin))
