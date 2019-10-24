from tclCommands.TclCommand import TclCommand

import collections
import logging

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class TclCommandScale(TclCommand):
    """
    Tcl shell command to resizes the object by a factor.

    example:
        scale my_geometry 4.2
    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['scale']

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str),
        ('factor', float)
    ])

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('x', float),
        ('y', float),
        ('origin', str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Resizes the object by a factor on X axis and a factor on Y axis, having as scale origin the point ",
        'args': collections.OrderedDict([
            ('name', 'Name of the object to resize.'),
            ('factor', 'Fraction by which to scale on both axis. '),
            ('x', 'Fraction by which to scale on X axis. If "factor" is used then this parameter is ignored'),
            ('y', 'Fraction by which to scale on Y axis. If "factor" is used then this parameter is ignored'),
            ('origin', 'Reference used for scale. It can be: "origin" which means point (0, 0) or "min_bounds" which '
                       'means the lower left point of the bounding box or it can be "center" which means the center '
                       'of the bounding box.')

        ]),
        'examples': ['scale my_geometry 4.2',
                     'scale my_geo -x 3.1 -y 2.8',
                     'scale my_geo 1.2 -origin min_bounds']
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """

        name = args['name']
        try:
            obj_to_scale = self.app.collection.get_by_name(name)
        except Exception as e:
            log.debug("TclCommandCopperClear.execute() --> %s" % str(e))
            self.raise_tcl_error("%s: %s" % (_("Could not retrieve box object"), name))
            return "Could not retrieve object: %s" % name

        if 'origin' not in args:
            xmin, ymin, xmax, ymax = obj_to_scale.bounds()
            c_x = xmin + (xmax - xmin) / 2
            c_y = ymin + (ymax - ymin) / 2
            point = (c_x, c_y)
        else:
            if args['origin'] == 'origin':
                point = (0, 0)
            elif args['origin'] == 'min_bounds':
                xmin, ymin, xmax, ymax = obj_to_scale.bounds()
                point = (xmin, ymin)
            elif args['origin'] == 'center':
                xmin, ymin, xmax, ymax = obj_to_scale.bounds()
                c_x = xmin + (xmax - xmin) / 2
                c_y = ymin + (ymax - ymin) / 2
                point = (c_x, c_y)
            else:
                self.raise_tcl_error('%s' % _("Expected -origin <origin> or -origin <min_bounds> or -origin <center>."))
                return 'fail'

        if 'factor' in args:
            factor = float(args['factor'])
            obj_to_scale.scale(factor, point=point)
            return

        if 'x' not in args and 'y' not in args:
            self.raise_tcl_error('%s' % _("Expected -x <value> -y <value>."))
            return 'fail'

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
