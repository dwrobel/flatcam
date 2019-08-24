from ObjectCollection import *
from tclCommands.TclCommand import TclCommand
import gettext
import FlatCAMTranslation as fcTranslate
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

    # dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str)
    ])

    # dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('outname', str),
        ('margin', float),
        ('rounded', bool)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Creates a Geometry object that surrounds the object.",
        'args': collections.OrderedDict([
            ('name', 'Object name for which to create bounding box. String'),
            ('outname', 'Name of the resulting Geometry object. String.'),
            ('margin', "Distance of the edges of the box to the nearest polygon."
                       "Float number."),
            ('rounded', "If the bounding box is to have rounded corners their radius is equal to the margin. "
                        "True or False.")
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

        if not isinstance(obj, FlatCAMGerber) and not isinstance(obj, FlatCAMGeometry):
            self.raise_tcl_error('%s %s: %s.' % (
                _("Expected FlatCAMGerber or FlatCAMGeometry, got"), name, type(obj)))

        if 'margin' not in args:
            args['margin'] = float(self.app.defaults["gerber_bboxmargin"])
        margin = args['margin']

        if 'rounded' not in args:
            args['rounded'] = self.app.defaults["gerber_bboxrounded"]
        rounded = args['rounded']

        del args['name']

        try:
            def geo_init(geo_obj, app_obj):
                assert isinstance(geo_obj, FlatCAMGeometry)

                # Bounding box with rounded corners
                geo = cascaded_union(obj.solid_geometry)
                bounding_box = geo.envelope.buffer(float(margin))
                if not rounded:  # Remove rounded corners
                    bounding_box = bounding_box.envelope
                geo_obj.solid_geometry = bounding_box

            self.app.new_object("geometry", args['outname'], geo_init)
        except Exception as e:
            return "Operation failed: %s" % str(e)
