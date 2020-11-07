from tclCommands.TclCommand import TclCommandSignaled

import collections


class TclCommandMirror(TclCommandSignaled):
    """
    Tcl shell command to mirror an object.
    """

    # array of all command aliases, to be able use
    # old names for backward compatibility (add_poly, add_polygon)
    aliases = ['mirror']

    description = '%s %s' % ("--", "Will mirror the geometry of a named object. Does not create a new object.")

    # Dictionary of types from Tcl command, needs to be ordered.
    # For positional arguments
    arg_names = collections.OrderedDict([
        ('name', str)
    ])

    # Dictionary of types from Tcl command, needs to be ordered.
    # For options like -optionname value
    option_types = collections.OrderedDict([
        ('axis', str),
        ('box', str),
        ('origin', str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Will mirror the geometry of a named object. Does not create a new object.",
        'args': collections.OrderedDict([
            ('name', 'Name of the object (Gerber, Geometry or Excellon) to be mirrored. Required.'),
            ('axis', 'Mirror axis parallel to the X or Y axis.'),
            ('box', 'Name of object which act as box (cutout for example.)'),
            ('origin', 'Reference point . It is used only if the box is not used. Format (x,y).\n'
                       'Comma will separate the X and Y coordinates.\n'
                       'WARNING: no spaces are allowed. If uncertain enclose the two values inside parenthesis.\n'
                       'See the example.')
        ]),
        'examples': ['mirror obj_name -box box_geo -axis X -origin 3.2,4.7']
    }

    def execute(self, args, unnamed_args):
        """
        Execute this TCL shell command

        :param args: array of known named arguments and options
        :param unnamed_args: array of other values which were passed into command
            without -somename and  we do not have them in known arg_names
        :return: None or exception
        """

        name = args['name']

        # Get source object.
        try:
            obj = self.app.collection.get_by_name(str(name))
        except Exception:
            return "Could not retrieve object: %s" % name

        if obj is None:
            return "Object not found: %s" % name

        if obj.kind != 'gerber' and obj.kind != 'geometry' and obj.kind != 'excellon':
            return "ERROR: Only Gerber, Excellon and Geometry objects can be mirrored."

        # Axis
        if 'axis' in args:
            try:
                axis = args['axis'].upper()
            except KeyError:
                axis = 'Y'
        else:
            axis = 'Y'

        # Box
        if 'box' in args:
            try:
                box = self.app.collection.get_by_name(args['box'])
            except Exception:
                return "Could not retrieve object: %s" % args['box']

            if box is None:
                return "Object box not found: %s" % args['box']

            try:
                xmin, ymin, xmax, ymax = box.bounds()
                px = 0.5 * (xmin + xmax)
                py = 0.5 * (ymin + ymax)

                obj.mirror(axis, [px, py])
                obj.plot()
                return
            except Exception as e:
                return "Operation failed: %s" % str(e)

        # Origin
        if 'origin' in args:
            try:
                origin_val = eval(args['origin'])
                x = float(origin_val[0])
                y = float(origin_val[1])
            except KeyError:
                x, y = (0, 0)
            except ValueError:
                return "Invalid distance: %s" % str(args['origin'])

            try:
                obj.mirror(axis, [x, y])
            except Exception as e:
                return "Operation failed: %s" % str(e)
