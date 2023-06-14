from tclCommands.TclCommand import TclCommand

import collections


class TclCommandOffset(TclCommand):
    """
    Tcl shell command to change the position of the object.

    example:
        offset my_geometry 1.2 -0.3
    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['offset']

    description = '%s %s' % ("--", "Will offset the geometry of named objects. Does not create a new object.")

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([

    ])

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('x', float),
        ('y', float)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = []

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Changes the position of the named object(s) on X and/or Y axis.\n"
                "The names of the objects to be offset will be entered after the command,\n"
                "separated by spaces. See the example below.\n"
                "WARNING: if the name of an object has spaces, enclose the name with quotes.",
        'args': collections.OrderedDict([
            ('x', 'Offset distance in the X axis. If it is not used it will be assumed to be 0.0'),
            ('y', 'Offset distance in the Y axis. If it is not used it will be assumed to be 0.0')
        ]),
        'examples': ['offset my_object_1 "my object_1" -x 1.2 -y -0.3', 'offset my_object -x 1.0']
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """

        off_x = args['x'] if 'x' in args else 0.0
        off_y = args['y'] if 'y' in args else 0.0

        x, y = float(off_x), float(off_y)

        if (x, y) == (0.0, 0.0):
            self.app.log.warning("Offset by 0.0. Nothing to be done.")
            return

        obj_names = unnamed_args
        if not obj_names:
            self.app.log.error("Missing objects to be offset. Exiting.")
            return "fail"

        for name in obj_names:
            obj = self.app.collection.get_by_name(str(name))
            if obj is None or obj == '':
                self.app.log.error("Object not found: %s" % name)
                return "fail"

            obj.offset((x, y))

            try:
                xmin, ymin, xmax, ymax = obj.bounds()
                obj.obj_options['xmin'] = xmin
                obj.obj_options['ymin'] = ymin
                obj.obj_options['xmax'] = xmax
                obj.obj_options['ymax'] = ymax
            except Exception as e:
                self.app.log.error("TclCommandOffset -> The object has no bounds properties. %s" % str(e))
                return "fail"
