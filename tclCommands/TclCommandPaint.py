from tclCommands.TclCommand import *


class TclCommandPaint(TclCommandSignaled):
    """
    Paint the interior of polygons
    """

    # Array of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['paint']

    # dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str),
        ('tooldia', float),
        ('overlap', float)
    ])

    # dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('outname', str),
        ('all', bool),
        ('x', float),
        ('y', float)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name', 'tooldia', 'overlap']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Paint polygons",
        'args': collections.OrderedDict([
            ('name', 'Name of the source Geometry object.'),
            ('tooldia', 'Diameter of the tool to be used.'),
            ('overlap', 'Fraction of the tool diameter to overlap cuts.'),
            ('outname', 'Name of the resulting Geometry object.'),
            ('all', 'Paint all polygons in the object.'),
            ('x', 'X value of coordinate for the selection of a single polygon.'),
            ('y', 'Y value of coordinate for the selection of a single polygon.')
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

        name = args['name']
        tooldia = args['tooldia']
        overlap = args['overlap']

        if 'outname' in args:
            outname = args['outname']
        else:
            outname = name + "_paint"

        obj = self.app.collection.get_by_name(name)
        if obj is None:
            self.raise_tcl_error("Object not found: %s" % name)

        if not isinstance(obj, Geometry):
            self.raise_tcl_error('Expected Geometry, got %s %s.' % (name, type(obj)))

        if 'all' in args and args['all']:
            obj.paint_poly_all(tooldia, overlap, outname)
            return

        if 'x' not in args or 'y' not in args:
            self.raise_tcl_error('Expected -all 1 or -x <value> and -y <value>.')

        x = args['x']
        y = args['y']

        obj.paint_poly_single_click([x, y], tooldia, overlap, outname)


