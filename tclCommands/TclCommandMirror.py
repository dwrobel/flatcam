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

    ])

    # Dictionary of types from Tcl command, needs to be ordered.
    # For options like -optionname value
    option_types = collections.OrderedDict([
        ('axis', str),
        ('box', str),
        ('origin', str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = []

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Will mirror the geometry of a named object. Does not create a new object.\n"
                "The names of the objects to be scaled will be entered after the command,\n"
                "separated by spaces. See the example below.\n"
                "WARNING: if the name of an object has spaces, enclose the name with quotes.",
        'args': collections.OrderedDict([
            ('axis', 'Mirror axis parallel to the X or Y axis.'),
            ('box', 'Name of object which act as box (cutout for example.)'),
            ('origin', 'Reference point . It is used only if the box is not used. Format (x,y).\n'
                       'The reference point can be:\n'
                       '- "origin" which means point (0, 0)\n'
                       '- "min_bounds" which means the lower left point of the bounding box made for all objects\n'
                       '- "center" which means the center point of the bounding box made for all objects.\n'
                       '- a point in format (x,y) with the X and Y coordinates separated by a comma. NO SPACES ALLOWED')
        ]),
        'examples': ['mirror obj_name -box box_geo -axis X',
                     'mirror obj_name -axis X -origin 3.2,4.7']
    }

    def execute(self, args, unnamed_args):
        """
        Execute this TCL shell command

        :param args: array of known named arguments and options
        :param unnamed_args: array of other values which were passed into command
            without -somename and  we do not have them in known arg_names
        :return: None or exception
        """

        obj_names = unnamed_args
        if not obj_names:
            self.app.log.error("Missing objects to be offset. Exiting.")
            return "fail"

        # calculate the bounds
        minx_lst = []
        miny_lst = []
        maxx_lst = []
        maxy_lst = []
        for name in obj_names:
            obj = self.app.collection.get_by_name(str(name))
            if obj is None or obj == '':
                self.app.log.error("Object not found: %s" % name)
                return "fail"
            a, b, c, d = obj.bounds()
            minx_lst.append(a)
            miny_lst.append(b)
            maxx_lst.append(c)
            maxy_lst.append(d)
        xmin = min(minx_lst)
        ymin = min(miny_lst)
        xmax = max(maxx_lst)
        ymax = max(maxy_lst)

        for name in obj_names:
            # Get source object.
            try:
                obj = self.app.collection.get_by_name(str(name))
            except Exception:
                self.app.log.error("Could not retrieve object: %s" % name)
                return "fail"

            if obj is None:
                self.app.log.error("Object not found: %s" % name)
                return "fail"

            if obj.kind != 'gerber' and obj.kind != 'geometry' and obj.kind != 'excellon':
                self.app.log.error("ERROR: Only Gerber, Excellon and Geometry objects can be mirrored.")
                return "fail"

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
                    self.app.log.error("Could not retrieve object: %s" % args['box'])
                    return "fail"

                if box is None:
                    self.app.log.error("Object box not found: %s" % args['box'])
                    return "fail"

                try:
                    xmin_b, ymin_b, xmax_b, ymax_b = box.bounds()
                    px = 0.5 * (xmin_b + xmax_b)
                    py = 0.5 * (ymin_b + ymax_b)

                    obj.mirror(axis, [px, py])
                    continue
                except Exception as e:
                    self.app.log.error("Operation failed: %s" % str(e))
                    return "fail"

            # Origin
            if 'origin' in args:
                if args['origin'] == 'origin':
                    x, y = (0, 0)
                elif args['origin'] == 'min_bounds':
                    x, y = (xmin, ymin)
                elif args['origin'] == 'center':
                    c_x = xmin + (xmax - xmin) / 2
                    c_y = ymin + (ymax - ymin) / 2
                    x, y = (c_x, c_y)
                else:
                    try:
                        origin_val = eval(args['origin'])
                        x = float(origin_val[0])
                        y = float(origin_val[1])
                    except KeyError:
                        x, y = (0, 0)
                    except ValueError:
                        self.app.log.error("Invalid distance: %s" % str(args['origin']))
                        return "fail"

                try:
                    obj.mirror(axis, [x, y])
                except Exception as e:
                    self.app.log.error("Operation failed: %s" % str(e))
                    return "fail"
