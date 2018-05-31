from tclCommands.TclCommand import *


class TclCommandAddCircle(TclCommand):
    """
    Tcl shell command to creates a circle in the given Geometry object.

    example:

    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['add_circle']

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str),
        ('center_x', float),
        ('center_y', float),
        ('radius', float)
    ])

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([

    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name', 'center_x', 'center_y', 'radius']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Creates a circle in the given Geometry object.",
        'args': collections.OrderedDict([
            ('name', 'Name of the geometry object to which to append the circle.'),
            ('center_x', 'X coordinate of the center of the circle.'),
            ('center_y', 'Y coordinates of the center of the circle.'),
            ('radius', 'Radius of the circle.')
        ]),
        'examples': []
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """

        obj_name = args['name']
        center_x = args['center_x']
        center_y = args['center_y']
        radius = args['radius']

        try:
            obj = self.app.collection.get_by_name(str(obj_name))
        except:
            return "Could not retrieve object: %s" % obj_name
        if obj is None:
            return "Object not found: %s" % obj_name

        obj.add_circle([float(center_x), float(center_y)], float(radius))

