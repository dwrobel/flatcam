from tclCommands.TclCommand import TclCommand
from FlatCAMObj import FlatCAMGeometry, FlatCAMGerber

from shapely.ops import cascaded_union

import collections

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class TclCommandNregions(TclCommand):
    """
    Tcl shell command to follow a Gerber file
    """

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = ['non_copper_regions', 'ncr']

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
        'main': "Creates a geometry object with the non-copper regions.",
        'args': collections.OrderedDict([
            ('name', 'Object name for which to create non-copper regions. String. Required.'),
            ('outname', 'Name of the resulting Geometry object. String.'),
            ('margin', "Specify the edge of the PCB by drawing a box around all objects with this minimum distance. "
                       "Float number."),
            ('rounded', "Resulting geometry will have rounded corners. True or False.")
        ]),
        'examples': ['ncr name -margin 0.1 -rounded True -outname name_ncr']
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
            args['outname'] = name + "_noncopper"

        obj = self.app.collection.get_by_name(name)
        if obj is None:
            self.raise_tcl_error("%s: %s" % (_("Object not found"), name))

        if not isinstance(obj, FlatCAMGerber) and not isinstance(obj, FlatCAMGeometry):
            self.raise_tcl_error('%s %s: %s.' % (_("Expected FlatCAMGerber or FlatCAMGeometry, got"), name, type(obj)))

        if 'margin' not in args:
            args['margin'] = float(self.app.defaults["gerber_noncoppermargin"])
        margin = float(args['margin'])

        if 'rounded' not in args:
            args['rounded'] = self.app.defaults["gerber_noncopperrounded"]
        rounded = bool(args['rounded'])

        del args['name']

        try:
            def geo_init(geo_obj, app_obj):
                assert isinstance(geo_obj, FlatCAMGeometry)

                geo = cascaded_union(obj.solid_geometry)
                bounding_box = geo.envelope.buffer(float(margin))
                if not rounded:
                    bounding_box = bounding_box.envelope

                non_copper = bounding_box.difference(geo)
                geo_obj.solid_geometry = non_copper

            self.app.new_object("geometry", args['outname'], geo_init, plot=False)
        except Exception as e:
            return "Operation failed: %s" % str(e)

        # in the end toggle the visibility of the origin object so we can see the generated Geometry
        self.app.collection.get_by_name(name).ui.plot_cb.toggle()
