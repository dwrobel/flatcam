from ObjectCollection import *
from tclCommands.TclCommand import TclCommandSignaled


class TclCommandMirror(TclCommandSignaled):
    """
    Tcl shell command to mirror an object.
    """

    # array of all command aliases, to be able use
    # old names for backward compatibility (add_poly, add_polygon)
    aliases = ['mirror']

    # Dictionary of types from Tcl command, needs to be ordered.
    # For positional arguments
    arg_names = collections.OrderedDict([
        ('name', str)
    ])

    # Dictionary of types from Tcl command, needs to be ordered.
    # For options like -optionname value
    option_types = collections.OrderedDict([
        ('axis', str),
        ('box', str),
        ('dist', float)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name', 'axis']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Opens an Excellon file.",
        'args': collections.OrderedDict([
            ('name', 'Name of the object (Gerber or Excellon) to mirror.'),
            ('box', 'Name of object which act as box (cutout for example.)'),
            ('axis', 'Mirror axis parallel to the X or Y axis.'),
            ('dist', 'Distance of the mirror axis to the X or Y axis.')
        ]),
        'examples': []
    }

    def execute(self, args, unnamed_args):
        """
        Execute this TCL shell command

        :param args: array of known named arguments and options
        :param unnamed_args: array of other values which were passed into command
            without -somename and  we do not have them in known arg_names
        :return: None or exception
        """

        name = args['name']

        # Get source object.
        try:
            obj = self.app.collection.get_by_name(str(name))
        except:
            return "Could not retrieve object: %s" % name

        if obj is None:
            return "Object not found: %s" % name

        if not isinstance(obj, FlatCAMGerber) and \
                not isinstance(obj, FlatCAMExcellon) and \
                not isinstance(obj, FlatCAMGeometry):
            return "ERROR: Only Gerber, Excellon and Geometry objects can be mirrored."

        # Axis
        try:
            axis = args['axis'].upper()
        except KeyError:
            return "ERROR: Specify -axis X or -axis Y"

        # Box
        if 'box' in args:
            try:
                box = self.app.collection.get_by_name(args['box'])
            except:
                return "Could not retrieve object box: %s" % args['box']

            if box is None:
                return "Object box not found: %s" % args['box']

            try:
                xmin, ymin, xmax, ymax = box.bounds()
                px = 0.5 * (xmin + xmax)
                py = 0.5 * (ymin + ymax)

                obj.mirror(axis, [px, py])
                obj.plot()

            except Exception as e:
                return "Operation failed: %s" % str(e)

        else:
            try:
                dist = float(args['dist'])
            except KeyError:
                dist = 0.0
            except ValueError:
                return "Invalid distance: %s" % args['dist']

            try:
                obj.mirror(axis, [dist, dist])
                obj.plot()
            except Exception as e:
                return "Operation failed: %s" % str(e)
