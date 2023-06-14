from tclCommands.TclCommand import TclCommand

import collections
import math

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


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

    ])

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('x', float),
        ('y', float),
        ('x_dist', float),
        ('y_dist', float),
        ('origin', str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = []

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Shear/Skew an object along x and y dimensions, having a specified skew origin"
                "The names of the objects to be scaled will be entered after the command,\n"
                "separated by spaces. See the example below.\n"
                "WARNING: if the name of an object has spaces, enclose the name with quotes.",
        'args': collections.OrderedDict([
            ('x', 'Angle in degrees by which to skew on the X axis. If it is not used it will be assumed to be 0.0'),
            ('y', 'Angle in degrees by which to skew on the Y axis. If it is not used it will be assumed to be 0.0'),
            ('x_dist', 'Distance to skew on the X axis. If it is not used it will be assumed to be 0.0'),
            ('y_dist', 'Distance to skew on the Y axis. If it is not used it will be assumed to be 0.0\n'
                       'WARNING: You either use the (x_dist, y_dist) pair or the (x, y). They can not be mixed.'),

            ('origin', 'Reference used for skew.\n'
                       'The reference point can be:\n'
                       '- "origin" which means point (0, 0)\n'
                       '- "min_bounds" which means the lower left point of the bounding box made for all objects\n'
                       '- "center" which means the center point of the bounding box made for all objects.\n'
                       '- a point in format (x,y) with the X and Y coordinates separated by a comma. NO SPACES ALLOWED')
        ]),
        'examples': ['skew my_obj1 "my obj_2" -x 10.2 -y 3.5',
                     'skew my_obj -x 3.0 -origin 3.0,2.1',
                     'skew my_obj -x 1.0 -origin min_bounds',
                     'skew my_obj1 "my obj2" -x_dist 3.0 -y_dist 1.0 -origin 3.0,2.1']
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """
        if ('x' in args or 'X' in args or 'y' in args or 'Y' in args) and ('x_dist' in args or 'y_dist' in args):
            self.app.log.error(
                '%s' % "You either use the (x_dist, y_dist) pair or the (x, y). They can not be mixed.")
            return 'fail'

        obj_names = unnamed_args
        if not obj_names:
            self.app.log.error("Missing objects to be offset. Exiting.")
            return "fail"

        use_angles = False
        use_distances = False

        try:
            angle_x = float(args['x'])
            use_angles = True
        except Exception:
            try:
                angle_x = float(args['X'])
                use_angles = True
            except Exception:
                angle_x = 0.0

        try:
            angle_y = float(args['y'])
            use_angles = True
        except Exception:
            try:
                angle_y = float(args['Y'])
                use_angles = True
            except Exception:
                angle_y = 0.0

        try:
            dist_x = float(args['x_dist'])
            use_distances = True
        except Exception:
            dist_x = 0.0

        try:
            dist_y = float(args['y_dist'])
            use_distances = True
        except Exception:
            dist_y = 0.0

        if use_angles is True:
            if angle_x == 0.0 and angle_y == 0.0:
                # nothing to be done
                return

        if use_distances is True:
            if dist_x == 0.0 and dist_y == 0.0:
                # nothing to be done
                return

        obj_names = unnamed_args
        if not obj_names:
            self.app.log.error("Missing objects to be skew. Exiting.")
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
                obj_to_skew = self.app.collection.get_by_name(name)
            except Exception as e:
                self.app.log.error("TclCommandCopperSkew.execute() --> %s" % str(e))
                self.app.log.error("Could not retrieve object: %s" % name)
                self.raise_tcl_error("%s: %s" % (_("Could not retrieve object"), name))
                return "fail"

            if obj_to_skew is None or obj_to_skew == '':
                self.app.log.error("Object not found: %s" % name)
                return "fail"

            if 'origin' not in args:
                ref_point = (0, 0)
            else:
                if args['origin'] == 'origin':
                    ref_point = (0, 0)
                elif args['origin'] == 'min_bounds':
                    ref_point = (xmin, ymin)
                elif args['origin'] == 'center':
                    c_x = xmin + (xmax - xmin) / 2
                    c_y = ymin + (ymax - ymin) / 2
                    ref_point = (c_x, c_y)
                else:
                    try:
                        ref_point = eval(str(args['origin']))
                        if not isinstance(ref_point, tuple):
                            self.app.log.error("The -origin value is not a tuple in format e.g 3.32,4.5")
                            return "fail"
                    except Exception as e:
                        self.raise_tcl_error('%s\n%s' % (_("Expected -origin <origin> or "
                                                           "-origin <min_bounds> or "
                                                           "-origin <center> or "
                                                           "- origin 3.0,4.2."), str(e)))
                        return 'fail'

            if use_distances:
                # determination of angle_x
                height = ymax - ymin
                angle_x = math.degrees(math.atan(dist_x/height))

                # determination of angle_y
                width = xmax - xmin
                angle_y = math.degrees(math.atan(dist_y/width))

            obj_to_skew.skew(angle_x, angle_y, point=ref_point)

            try:
                xmin, ymin, xmax, ymax = obj_to_skew.bounds()
                obj_to_skew.obj_options['xmin'] = xmin
                obj_to_skew.obj_options['ymin'] = ymin
                obj_to_skew.obj_options['xmax'] = xmax
                obj_to_skew.obj_options['ymax'] = ymax
            except Exception as e:
                self.app.log.error("TclCommandSkew -> The object has no bounds properties. %s" % str(e))
                return "fail"
