import collections
from tclCommands.TclCommand import TclCommandSignaled

from shapely.geometry import Point
import shapely.affinity as affinity


class TclCommandAlignDrill(TclCommandSignaled):
    """
    Tcl shell command to create excellon with drills for aligment.
    """

    # array of all command aliases, to be able use  old names for
    # backward compatibility (add_poly, add_polygon)
    aliases = ['aligndrill']

    description = '%s %s' % ("--", "Create an Excellon object with drills for alignment.")

    # Dictionary of types from Tcl command, needs to be ordered.
    # For positional arguments
    arg_names = collections.OrderedDict([
        ('name', str)
    ])

    # Dictionary of types from Tcl command, needs to be ordered.
    # For options like -optionname value
    option_types = collections.OrderedDict([
        ('box', str),
        ('axis', str),
        ('holes', str),
        ('grid', float),
        ('minoffset', float),
        ('gridoffset', float),
        ('axisoffset', float),
        ('dia', float),
        ('dist', float),
        ('outname', str),
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name', 'axis']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Create an Excellon object with drills for alignment.",
        'args': collections.OrderedDict([
            ('name', 'Name of the object (Gerber or Excellon) to mirror.'),
            ('dia', 'Tool diameter'),
            ('box', 'Name of object which act as box (cutout for example.)'),
            ('holes', 'Tuple of tuples where each tuple it is a set of x, y coordinates. '
                      'E.g: (x0, y0), (x1, y1), ... '),
            ('grid', 'Aligning to grid, for those, who have aligning pins'
                     'inside table in grid (-5,0),(5,0),(15,0)...'),
            ('gridoffset', 'offset of grid from 0 position.'),
            ('minoffset', 'min and max distance between align hole and pcb.'),
            ('axisoffset', 'Offset on second axis before aligment holes'),
            ('axis', 'Mirror axis parallel to the X or Y axis.'),
            ('dist', 'Distance of the mirror axis to the X or Y axis.'),
            ('outname', 'Name of the resulting Excellon object.'),
        ]),
        'examples': ['aligndrill my_object -axis X -box my_object -dia 3.125 -grid 1 '
                     '-gridoffset 0 -minoffset 2 -axisoffset 2']
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

        if 'outname' in args:
            outname = args['outname']
        else:
            outname = name + "_aligndrill"

        # Get source object.
        try:
            obj = self.app.collection.get_by_name(str(name))
        except Exception:
            return "Could not retrieve object: %s" % name

        if obj is None:
            return "Object not found: %s" % name

        if obj.kind != "geometry" and obj.kind != 'gerber' and obj.kind != 'excellon':
            return "ERROR: Only Gerber, Geometry and Excellon objects can be used."

        # Axis
        try:
            axis = args['axis'].upper()
        except KeyError:
            return "ERROR: Specify -axis X or -axis Y"

        if not ('holes' in args or ('grid' in args and 'gridoffset' in args)):
            return "ERROR: Specify -holes or -grid with -gridoffset "

        if 'holes' in args:
            try:
                holes = eval("[" + args['holes'] + "]")
            except KeyError:
                return "ERROR: Wrong -holes format (X1,Y1),(X2,Y2)"

        xscale, yscale = {"X": (1.0, -1.0), "Y": (-1.0, 1.0)}[axis]

        tooldia = args['dia']

        # Tools
        # tools = {"1": {"C": args['dia']}}

        def alligndrill_init_me(init_obj, app_obj):
            """
            This function is used to initialize the new
            object once it's created.

            :param init_obj: The new object.
            :param app_obj: The application (FlatCAMApp)
            :return: None
            """

            drills = []
            if 'holes' in args:
                for hole in holes:
                    point = Point(hole)
                    point_mirror = affinity.scale(point, xscale, yscale, origin=(px, py))
                    drills.append(point)
                    drills.append(point_mirror)
            else:
                if 'box' not in args:
                    return "ERROR: -grid can be used only for -box"

                if 'axisoffset' in args:
                    axisoffset = args['axisoffset']
                else:
                    axisoffset = 0

                # This will align hole to given aligngridoffset and minimal offset from pcb, based on selected axis
                if axis == "X":
                    firstpoint = args['gridoffset']

                    while (xmin - args['minoffset']) < firstpoint:
                        firstpoint = firstpoint - args['grid']

                    lastpoint = args['gridoffset']

                    while (xmax + args['minoffset']) > lastpoint:
                        lastpoint = lastpoint + args['grid']

                    localholes = (firstpoint, axisoffset), (lastpoint, axisoffset)

                else:
                    firstpoint = args['gridoffset']

                    while (ymin - args['minoffset']) < firstpoint:
                        firstpoint = firstpoint - args['grid']

                    lastpoint = args['gridoffset']

                    while (ymax + args['minoffset']) > lastpoint:
                        lastpoint = lastpoint + args['grid']

                    localholes = (axisoffset, firstpoint), (axisoffset, lastpoint)

                for hole in localholes:
                    point = Point(hole)
                    point_mirror = affinity.scale(point, xscale, yscale, origin=(px, py))
                    drills.append(point)
                    drills.append(point_mirror)

            init_obj.tools = {
                '1': {
                    'tooldia': tooldia,
                    'drills': drills,
                    'solid_geometry': []
                }
            }

            init_obj.create_geometry()

        # Box
        if 'box' in args:
            try:
                box = self.app.collection.get_by_name(args['box'])
            except Exception:
                return "Could not retrieve object box: %s" % args['box']

            if box is None:
                return "Object box not found: %s" % args['box']

            try:
                xmin, ymin, xmax, ymax = box.bounds()
                px = 0.5 * (xmin + xmax)
                py = 0.5 * (ymin + ymax)

                obj.app.app_obj.new_object("excellon", outname, alligndrill_init_me, plot=False)

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
                px = dist
                py = dist
                obj.app.app_obj.new_object("excellon", outname, alligndrill_init_me, plot=False)
            except Exception as e:
                return "Operation failed: %s" % str(e)

        return 'Ok. Align Drills Excellon object created'
