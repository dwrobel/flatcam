from ObjectCollection import *
import TclCommand


class TclCommandGeoCutout(TclCommand.TclCommandSignaled):
    """
    Tcl shell command to cut holding gaps from geometry.
    """

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = ['geocutout']

    # Dictionary of types from Tcl command, needs to be ordered.
    # For positional arguments
    arg_names = collections.OrderedDict([
        ('name', str)
    ])

    # Dictionary of types from Tcl command, needs to be ordered.
    # For options like -optionname value
    option_types = collections.OrderedDict([
        ('dia', float),
        ('margin', float),
        ('gapsize', float),
        ('gaps', str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Cut holding gaps from geometry.",
        'args': collections.OrderedDict([
            ('name', 'Name of the geometry object.'),
            ('dia', 'Tool diameter.'),
            ('margin', 'Margin over bounds.'),
            ('gapsize', 'Size of gap.'),
            ('gaps', 'Type of gaps.'),
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

        # How gaps wil be rendered:
        # lr    - left + right
        # tb    - top + bottom
        # 4     - left + right +top + bottom
        # 2lr   - 2*left + 2*right
        # 2tb   - 2*top + 2*bottom
        # 8     - 2*left + 2*right +2*top + 2*bottom

        self.raise_tcl_error("Not implemented.")

        def subtract_rectangle(*args):
            pass

        name = args['name']

        try:
            obj = self.app.collection.get_by_name(str(name))
        except:
            self.raise_tcl_error("Could not retrieve object: %s" % name)

            # Get min and max data for each object as we just cut rectangles across X or Y
            xmin, ymin, xmax, ymax = obj.bounds()
            px = 0.5 * (xmin + xmax)
            py = 0.5 * (ymin + ymax)
            lenghtx = (xmax - xmin)
            lenghty = (ymax - ymin)
            gapsize = args['gapsize'] + args['dia'] / 2

            if args['gaps'] == '8' or args['gaps'] == '2lr':
                subtract_rectangle(name,
                                   xmin - gapsize,
                                   py - gapsize + lenghty / 4,
                                   xmax + gapsize,
                                   py + gapsize + lenghty / 4)
                subtract_rectangle(name,
                                   xmin - gapsize,
                                   py - gapsize - lenghty / 4,
                                   xmax + gapsize,
                                   py + gapsize - lenghty / 4)

            if args['gaps'] == '8' or args['gaps'] == '2tb':
                subtract_rectangle(name,
                                   px - gapsize + lenghtx / 4,
                                   ymin - gapsize,
                                   px + gapsize + lenghtx / 4,
                                   ymax + gapsize)
                subtract_rectangle(name,
                                   px - gapsize - lenghtx / 4,
                                   ymin - gapsize,
                                   px + gapsize - lenghtx / 4,
                                   ymax + gapsize)

            if args['gaps'] == '4' or args['gaps'] == 'lr':
                subtract_rectangle(name,
                                   xmin - gapsize,
                                   py - gapsize,
                                   xmax + gapsize,
                                   py + gapsize)

            if args['gaps'] == '4' or args['gaps'] == 'tb':
                subtract_rectangle(name,
                                   px - gapsize,
                                   ymin - gapsize,
                                   px + gapsize,
                                   ymax + gapsize)
