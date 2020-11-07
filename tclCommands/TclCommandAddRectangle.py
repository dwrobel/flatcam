from tclCommands.TclCommand import *


class TclCommandAddRectangle(TclCommandSignaled):
    """
    Tcl shell command to add a rectange to the given Geometry object.
    """

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = ['add_rectangle']

    description = '%s %s' % ("--", "Creates a rectangle in the given Geometry object.")

    # Dictionary of types from Tcl command, needs to be ordered.
    # For positional arguments
    arg_names = collections.OrderedDict([
        ('name', str),
        ('x0', float),
        ('y0', float),
        ('x1', float),
        ('y1', float)
    ])

    # Dictionary of types from Tcl command, needs to be ordered.
    # For options like -optionname value
    option_types = collections.OrderedDict([

    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name', 'x0', 'y0', 'x1', 'y1']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Creates a rectangle in the given Geometry object.",
        'args': collections.OrderedDict([
            ('name', 'Name of the Geometry object in which to add the rectangle.'),
            ('x0 y0', 'Bottom left corner coordinates.'),
            ('x1 y1', 'Top right corner coordinates.')
        ]),
        'examples': ["add_rectangle geo_name 0 0 10 10"]
    }

    def execute(self, args, unnamed_args):
        """
        execute current TCL shell command

        :param args: array of known named arguments and options
        :param unnamed_args: array of other values which were passed into command
            without -somename and  we do not have them in known arg_names
        :return: None or exception
        """

        name = args['name']
        x0 = args['x0']
        y0 = args['y0']
        x1 = args['x1']
        y1 = args['y1']

        if unnamed_args:
            self.raise_tcl_error(
                "Too many arguments. Correct format: %s" % '["add_rectangle geo_name xmin ymin xmax ymax"]')

        try:
            obj = self.app.collection.get_by_name(str(name))
        except Exception:
            return "Could not retrieve object: %s" % name
        if obj is None:
            return "Object not found: %s" % name
        if obj.kind != 'geometry':
            self.raise_tcl_error('Expected Geometry, got %s %s.' % (name, type(obj)))

        obj.add_polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
