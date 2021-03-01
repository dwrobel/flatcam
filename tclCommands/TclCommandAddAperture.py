from tclCommands.TclCommand import *
import math


class TclCommandAddAperture(TclCommandSignaled):
    """
    Tcl shell command to add a rectange to the given Geometry object.
    """

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = ['add_aperture']

    description = '%s %s' % ("--", "Adds an aperture in the given Gerber object, if it does not exist already.")

    # Dictionary of types from Tcl command, needs to be ordered.
    # For positional arguments
    arg_names = collections.OrderedDict([
        ('name', str)
    ])

    # Dictionary of types from Tcl command, needs to be ordered.
    # For options like -optionname value
    option_types = collections.OrderedDict([
        ('apid', int),
        ('type', str),
        ('size', float),
        ('width', float),
        ('height', float)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Creates an aperture in the given Gerber object.",
        'args': collections.OrderedDict([
            ('name', 'Name of the Gerber object in which to add the aperture.'),
            ('apid', 'Aperture ID. If not used then it will add one automatically.'),
            ('type', "Aperture Type. It can be letter 'C' or 'R' or 'O'. "
                     "If not used then it will use 'C' by default."),
            ('size', "The aperture size. Used only if aperture type is 'C'."),
            ('width', "Aperture width. Used only if aperture type is 'R' or 'O'."),
            ('height', "Aperture height. Used only if aperture type is 'R' or 'O'.")
        ]),
        'examples': ["add_aperture gerber_name -apid 10 -type 'C' -size 1.0"]
    }

    def execute(self, args, unnamed_args):
        """
        execute current TCL shell command

        :param args:            array of known named arguments and options
        :param unnamed_args:    array of other values which were passed into command
                                without -somename and  we do not have them in known arg_names
        :return:                None or exception
        """

        if unnamed_args:
            self.raise_tcl_error(
                "Too many arguments. Correct format: %s" %
                '["add_aperture gerber_name -apid -type -size -width -height"]')

        name = args['name']
        try:
            obj = self.app.collection.get_by_name(str(name))
        except Exception:
            return "Could not retrieve object: %s" % name
        if obj is None:
            return "Object not found: %s" % name
        if obj.kind != 'gerber':
            return 'Expected Gerber, got %s %s.' % (name, type(obj))

        obj_apertures_keys = list(obj.tools.keys())
        if 'apid' in args:
            new_apid = args['apid']
        else:
            ap_list = [int(ap) for ap in obj_apertures_keys]
            max_ap = max(ap_list)
            # we can't have aperture ID's between 0 an 10
            new_apid = 10 if max_ap == 0 else (max_ap + 1)

        if str(new_apid) in obj_apertures_keys:
            return "The aperture is already used. Try another 'apid' parameter value."

        if 'type' in args:
            try:
                # if it's a string using the quotes
                new_type = eval(args['type'])
            except NameError:
                # if it's a string without quotes
                new_type = args['type']
        else:
            new_type = 'C'
        if new_type == 'C':
            new_size = args['size'] if 'size' in args else 0.6
            obj.tools[str(new_apid)] = {
                'type': new_type,
                'size': new_size,
                'geometry': []
            }
        elif new_type in ['R', 'O']:
            new_width = args['width'] if 'width' in args else 0.0
            new_height = args['height'] if 'height' in args else 0.0
            new_size = math.sqrt(new_width ** 2 + new_height ** 2) if new_width > 0 and new_height > 0 else 0

            obj.tools[str(new_apid)] = {
                'type': new_type,
                'size': new_size,
                'width': new_width,
                'height': new_height,
                'geometry': []
            }
        else:
            return 'The supported aperture types are: C=circular, R=rectangular, O=oblong'

        print(obj.tools)