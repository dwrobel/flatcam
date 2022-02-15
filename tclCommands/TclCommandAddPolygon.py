from tclCommands.TclCommand import *


class TclCommandAddPolygon(TclCommandSignaled):
    """
    Tcl shell command to create a polygon in the given Geometry object
    """

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = ['add_polygon', 'add_poly']

    description = '%s %s' % ("--", "Creates a polygon in the given Geometry object.")

    # dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str)
    ])

    # dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('p_coords', str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Creates a polygon in the given Geometry object.",
        'args': collections.OrderedDict([
            ('name', 'Name of the Geometry object to which to append the polygon.'),
            ('p_coords', 'Optional. If used it needs to be a list of tuple point coords (x,y). '
                         'Brackets: "[" or "]" are not allowed. If spaces are used then enclose with quotes.'),
            ('xi, yi', 'Coordinates of points in the polygon.')
        ]),
        'examples': [
            'add_polygon <name> <x0> <y0> <x1> <y1> <x2> <y2> [x3 y3 [...]]',
            'add_poly <name> -p_coords "(5.0, 5.0), (6.0, 5.0), (6.0, 6.0), (5.0, 6.0), (5.0, 5.0)"'
        ]
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
        obj = self.app.collection.get_by_name(name)
        if obj is None:
            self.raise_tcl_error("Object not found: %s" % name)

        if obj.kind != 'geometry':
            self.raise_tcl_error('Expected Geometry, got %s %s.' % (name, type(obj)))

        if 'p_coords' in args:
            try:
                points = list(eval(args['p_coords']))
            except Exception as err:
                self.app.log.error("TclCommandAddPolygon.execute() -> %s" % str(err))
                return

            obj.add_polygon(points)
        elif len(unnamed_args) % 2 != 0:
            self.raise_tcl_error("Incomplete coordinates.")

            nr_points = int(len(unnamed_args) / 2)
            points = [[float(unnamed_args[2*i]), float(unnamed_args[2*i+1])] for i in range(nr_points)]

            obj.add_polygon(points)
