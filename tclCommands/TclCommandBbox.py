import collections
from tclCommands.TclCommand import TclCommand

from shapely.ops import unary_union

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class TclCommandBbox(TclCommand):
    """
    Tcl shell command to follow a Gerber file
    """

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = ['bounding_box', 'bbox']

    description = '%s %s' % ("--", "Creates a rectangular Geometry object that surrounds the object.")

    # dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str)
    ])

    # dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('outname', str),
        ('margin', float),
        ('rounded', str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Creates a rectangular Geometry object that surrounds the object.",
        'args': collections.OrderedDict([
            ('name', 'Object name for which to create bounding box. String'),
            ('margin', "Distance of the edges of the box to the nearest polygon."
                       "Float number."),
            ('rounded', "If the bounding box has to have rounded corners their radius is equal to the margin. "
                        "True (1) or False (0)."),
            ('outname', 'Name of the resulting Geometry object. String.')
        ]),
        'examples': ['bbox name -outname name_bbox']
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

        if 'outname' not in args:
            args['outname'] = name + "_bbox"

        obj = self.app.collection.get_by_name(name)
        if obj is None:
            self.raise_tcl_error("%s: %s" % (_("Object not found"), name))

        if obj.kind != 'gerber' and obj.kind != 'geometry':
            self.raise_tcl_error('%s %s: %s.' % (
                _("Expected GerberObject or GeometryObject, got"), name, type(obj)))

        if 'margin' not in args:
            args['margin'] = float(self.app.defaults["gerber_bboxmargin"])
        margin = args['margin']

        if 'rounded' in args:
            try:
                par = args['rounded'].capitalize()
            except AttributeError:
                par = args['rounded']
            rounded = bool(eval(par))
        else:
            rounded = bool(eval(self.app.defaults["gerber_bboxrounded"]))

        del args['name']

        try:
            def geo_init(geo_obj, app_obj):
                # assert geo_obj.kind == 'geometry'

                # Bounding box with rounded corners
                geo = unary_union(obj.solid_geometry)
                bounding_box = geo.envelope.buffer(float(margin))
                if not rounded:  # Remove rounded corners
                    bounding_box = bounding_box.envelope
                geo_obj.solid_geometry = bounding_box

            self.app.app_obj.new_object("geometry", args['outname'], geo_init, plot=False)
        except Exception as e:
            return "Operation failed: %s" % str(e)
