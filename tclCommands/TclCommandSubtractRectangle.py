from tclCommands.TclCommand import TclCommandSignaled

import collections

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class TclCommandSubtractRectangle(TclCommandSignaled):
    """
    Tcl shell command to subtract a rectangle from the given Geometry object.
    """

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = ['subtract_rectangle']

    # Dictionary of types from Tcl command, needs to be ordered.
    # For positional arguments
    arg_names = collections.OrderedDict([
        ('name', str)
    ])

    # Dictionary of types from Tcl command, needs to be ordered.
    # For options like -optionname value
    option_types = collections.OrderedDict([

    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Subtract rectange from the given Geometry object.",
        'args': collections.OrderedDict([
            ('name', 'Name of the Geometry object from which to subtract.'),
            ('x0 y0', 'Bottom left corner coordinates.'),
            ('x1 y1', 'Top right corner coordinates.')
        ]),
        'examples': ['subtract_rectangle geo_obj 8 8 15 15']
    }

    def execute(self, args, unnamed_args):
        """
        execute current TCL shell command

        :param args: array of known named arguments and options
        :param unnamed_args: array of other values which were passed into command
            without -somename and  we do not have them in known arg_names
        :return: None or exception
        """
        if 'name' not in args:
            self.raise_tcl_error("%s:" % _("No Geometry name in args. Provide a name and try again."))
            return 'fail'
        obj_name = args['name']

        if len(unnamed_args) != 4:
            self.raise_tcl_error("Incomplete coordinates. There are 4 required: x0 y0 x1 y1.")
            return 'fail'

        x0 = float(unnamed_args[0])
        y0 = float(unnamed_args[1])
        x1 = float(unnamed_args[2])
        y1 = float(unnamed_args[3])

        try:
            obj = self.app.collection.get_by_name(str(obj_name))
        except Exception as e:
            return "Could not retrieve object: %s" % obj_name
        if obj is None:
            return "Object not found: %s" % obj_name

        obj.subtract_polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
