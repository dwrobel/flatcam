from tclCommands.TclCommand import TclCommand

import collections
import logging

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class TclCommandBuffer(TclCommand):
    """
    Tcl shell command to buffer the object by a distance or to scale each geometric element using the center of
    its individual bounding box as a reference.

    example:
        # buffer each geometric element at the distance 4.2 in the my_geo Geometry obj
        buffer my_geo -distance 4.2
        # scale each geo element by a factor of 4.2 in the my_geo Geometry obj and the join is 2 (square)
        buffer my_geo -distance 4.2 -factor True -join 2
    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['buffer']

    description = '%s %s' % ("--", "Will buffer the geometry of a named object. Does not create a new object.")

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str)
    ])

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('dist', float),
        ('join', str),
        ('factor', str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name', 'dist']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Works only on Geometry, Gerber and Excellon objects.\n"
                "Buffer the object by a distance or to scale each geometric element using \n"
                "the center of its individual bounding box as a reference.\n"
                "If 'factor' is True(1) then 'dist' is the scale factor for each geometric element.",
        'args': collections.OrderedDict([
            ('name', 'Name of the Geometry, Gerber or Excellon object to be buffered. Required.'),
            ('dist', 'Distance to which to buffer each geometric element.'),
            ('join', 'How two lines join and make a corner: round (1), square (2) or bevel (3). Default is: round'),
            ('factor', "If 'factor' is True(1) then the 'distance' parameter\n"
                       "is the scale factor for each geometric element that is scaled (individually)")

        ]),
        'examples': [
            '# buffer each geometric element at the distance 4.2 in the my_geo Geometry obj'
            'buffer my_geo -dist 4.2 ',
            '# scale each geo element by a factor of 4.2 in the my_geo Geometry obj',
            'buffer my_geo -dist 4.2 -factor True',
            'buffer my_geo -dist 4.2 -factor 1',
            '# scale each geo element by a factor of 4.2 in the my_geo Geometry obj and the join is 2 (square)',
            'buffer my_geo -dist 4.2 -factor True -join 2'
        ]
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """

        name = args['name']
        try:
            obj_to_buff = self.app.collection.get_by_name(name)
        except Exception as e:
            self.app.log.error("TclCommandCopperBuffer.execute() --> %s" % str(e))
            self.raise_tcl_error("%s: %s" % (_("Could not retrieve object"), name))
            return "Could not retrieve object: %s" % name

        if obj_to_buff.kind not in ['geometry', 'excellon', 'gerber']:
            self.app.log.error("%s: %s %s" % ("The object", name, "can be only of type Geometry, Gerber or Excellon."))
            self.raise_tcl_error(
                "%s: %s %s" % ("The object", name, "can be only of type Geometry, Gerber or Excellon."))
            return "%s: %s %s" % ("The object", name, "can be only of type Geometry, Gerber or Excellon.")

        if 'dist' not in args:
            self.raise_tcl_error('%s' % _("Expected -dist <value>"))
            return 'fail'

        distance = args['dist']
        if 'join' not in args:
            join = 1
        else:
            if args['join'] in ['square', 'Square', '2', 2]:
                join = 2
            elif args['join'] in ['bevel', 'Bevel', '3', 3]:
                join = 3
            else:
                join = 1
        factor = bool(eval(str(args['factor']).capitalize())) if 'factor' in args else None

        obj_to_buff.buffer(distance, join, factor, only_exterior=True)

        try:
            xmin, ymin, xmax, ymax = obj_to_buff.bounds()
            obj_to_buff.obj_options['xmin'] = xmin
            obj_to_buff.obj_options['ymin'] = ymin
            obj_to_buff.obj_options['xmax'] = xmax
            obj_to_buff.obj_options['ymax'] = ymax
        except Exception as e:
            self.app.log.error("TclCommandBuffer -> The object has no bounds properties. %s" % str(e))
            return "fail"
