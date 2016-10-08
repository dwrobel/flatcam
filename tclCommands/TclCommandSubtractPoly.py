from ObjectCollection import *
import TclCommand


class TclCommandSubtractPoly(TclCommand.TclCommandSignaled):
    """
    Tcl shell command to create a new empty Geometry object.
    """

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = ['subtract_poly']

    # Dictionary of types from Tcl command, needs to be ordered.
    # For positional arguments
    arg_names = collections.OrderedDict([
        ('name', str)
    ])

    # Dictionary of types from Tcl command, needs to be ordered.
    # For options like -optionname value
    option_types = collections.OrderedDict([

    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Subtract polygon from the given Geometry object.",
        'args': collections.OrderedDict([
            ('name', 'Name of the Geometry object from which to subtract.'),
            ('x0 y0 x1 y1 x2 y2 ...', 'Points defining the polygon.')
        ]),
        'examples': []
    }

    def execute(self, args, unnamed_args):
        """
        execute current TCL shell command

        :param args: array of known named arguments and options
        :param unnamed_args: array of other values which were passed into command
            without -somename and  we do not have them in known arg_names
        :return: None or exception
        """

        obj_name = args['name']

        if len(unnamed_args) % 2 != 0:
            return "Incomplete coordinate."

        points = [[float(unnamed_args[2 * i]), float(unnamed_args[2 * i + 1])] for i in range(len(unnamed_args) / 2)]

        try:
            obj = self.app.collection.get_by_name(str(obj_name))
        except:
            return "Could not retrieve object: %s" % obj_name
        if obj is None:
            return "Object not found: %s" % obj_name

        obj.subtract_polygon(points)
