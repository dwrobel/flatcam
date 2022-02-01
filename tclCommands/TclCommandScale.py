from tclCommands.TclCommand import TclCommand

import collections

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class TclCommandScale(TclCommand):
    """
    Tcl shell command to resizes the object by a factor.

    example:
        scale my_geometry 4.2
    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['scale']

    description = '%s %s' % ("--", "Will scale the geometry of named objects. Does not create a new object.")

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([

    ])

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('factor', float),
        ('x', float),
        ('y', float),
        ('origin', str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Resizes objects by a factor on X axis and a factor on Y axis, having a specified scale origin\n"
                "The names of the objects to be scaled will be entered after the command,\n"
                "separated by spaces. See the example below.\n"
                "WARNING: if the name of an object has spaces, enclose the name with quotes.",
        'args': collections.OrderedDict([
            ('factor', 'Fraction by which to scale on both axis.'),
            ('x', 'Fraction by which to scale on X axis. If "factor" is used then this parameter is ignored'),
            ('y', 'Fraction by which to scale on Y axis. If "factor" is used then this parameter is ignored'),
            ('origin', 'Reference used for scale.\n'
                       'The reference point can be:\n'
                       '- "origin" which means point (0, 0)\n'
                       '- "min_bounds" which means the lower left point of the bounding box made for all objects\n'
                       '- "center" which means the center point of the bounding box made for all objects.\n'
                       '- a point in format (x,y) with the X and Y coordinates separated by a comma. NO SPACES ALLOWED')

        ]),
        'examples': ['scale my_obj_1 "my obj_2" -factor 4.2',
                     'scale my_obj -x 3.1 -y 2.8',
                     'scale my_obj -factor 1.2 -origin min_bounds',
                     'scale my_object -x 2 -origin 3.0,2.1']
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """
        if ('x' not in args or 'X' not in args) and ('y' not in args or 'Y' not in args) and 'factor' not in args:
            self.app.log.warning('%s' % "Expected -x <value> -y <value> or -factor <value>")
            self.raise_tcl_error('%s' % "Expected -x <value> -y <value> or -factor <value>")
            return 'fail'

        obj_names = unnamed_args
        if not obj_names:
            self.app.log.error("Missing objects to be scale. Exiting.")
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
            try:
                obj_to_scale = self.app.collection.get_by_name(name)
            except Exception as e:
                self.app.log.error("TclCommandCopperScale.execute() --> %s" % str(e))
                self.app.log.error("Could not retrieve object: %s" % name)
                self.raise_tcl_error("%s: %s" % (_("Could not retrieve object"), name))
                return "fail"

            if obj_to_scale is None or obj_to_scale == '':
                self.app.log.error("Object not found: %s" % name)
                return "fail"

            if 'origin' not in args:
                c_x = xmin + (xmax - xmin) / 2
                c_y = ymin + (ymax - ymin) / 2
                point = (c_x, c_y)
            else:
                if args['origin'] == 'origin':
                    point = (0, 0)
                elif args['origin'] == 'min_bounds':
                    point = (xmin, ymin)
                elif args['origin'] == 'center':
                    c_x = xmin + (xmax - xmin) / 2
                    c_y = ymin + (ymax - ymin) / 2
                    point = (c_x, c_y)
                else:
                    try:
                        point = eval(str(args['origin']))
                        if not isinstance(point, tuple):
                            self.app.log.error("The -origin value is not a tuple in format e.g 3.32,4.5")
                            return "fail"
                    except Exception as e:
                        self.raise_tcl_error('%s\n%s' % (_("Expected -origin <origin> or "
                                                           "-origin <min_bounds> or "
                                                           "-origin <center> or "
                                                           "- origin 3.0,4.2."), str(e)))
                        return 'fail'

            if 'factor' in args:
                factor = float(args['factor'])
                obj_to_scale.scale(factor, point=point)
                continue

            if 'x' in args and 'y' not in args:
                f_x = float(args['x'])
                obj_to_scale.scale(f_x, 0, point=point)
            elif 'x' not in args and 'y' in args:
                f_y = float(args['y'])
                obj_to_scale.scale(0, f_y, point=point)
            elif 'x' in args and 'y' in args:
                f_x = float(args['x'])
                f_y = float(args['y'])
                obj_to_scale.scale(f_x, f_y, point=point)
