import collections
from tclCommands.TclCommand import TclCommandSignaled

from shapely.geometry import Point

class TclCommandAlignDrillGrid(TclCommandSignaled):
    """
    Tcl shell command to create an Excellon object
    with drills for aligment grid.

    Todo: What is an alignment grid?
    """

    # array of all command aliases, to be able use  old names for
    # backward compatibility (add_poly, add_polygon)
    aliases = ['aligndrillgrid']

    description = '%s %s' % ("--", "Create an Excellon object with drills for alignment arranged in a grid.")

    # Dictionary of types from Tcl command, needs to be ordered.
    # For positional arguments
    arg_names = collections.OrderedDict([

    ])

    # Dictionary of types from Tcl command, needs to be ordered.
    # For options like -optionname value
    option_types = collections.OrderedDict([
        ('dia', float),
        ('gridx', float),
        ('gridoffsetx', float),
        ('gridy', float),
        ('gridoffsety', float),
        ('columns', int),
        ('rows', int),
        ('outname', str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['gridx', 'gridy', 'columns', 'rows']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Create an Excellon object with drills for alignment arranged in a grid.",
        'args': collections.OrderedDict([
            ('dia', 'Tool diameter.'),
            ('gridx', 'Grid size in X axis.'),
            ('gridoffsetx', 'Move grid  from origin.'),
            ('gridy', 'Grid size in Y axis.'),
            ('gridoffsety', 'Move grid  from origin.'),
            ('colums', 'Number of grid holes on X axis.'),
            ('rows', 'Number of grid holes on Y axis.'),
            ('outname', 'Name of the object to create.')
        ]),
        'examples': ['aligndrillgrid -rows 2 -columns 2 -gridoffsetx 10 -gridoffsety 10 -gridx 2.54 -gridy 5.08']
    }

    def execute(self, args, unnamed_args):
        """
        execute current TCL shell command

        :param args: array of known named arguments and options
        :param unnamed_args: array of other values which were passed into command
            without -somename and  we do not have them in known arg_names
        :return: None or exception
        """

        if 'outname' in args:
            outname = args['outname']
        else:
            outname = "new_aligndrill_grid"

        if 'gridoffsetx' not in args:
            gridoffsetx = 0
        else:
            gridoffsetx = args['gridoffsetx']

        if 'gridoffsety' not in args:
            gridoffsety = 0
        else:
            gridoffsety = args['gridoffsety']

        tooldia = args['dia']
        # Tools
        # tools = {"1": {"C": args['dia']}}

        def aligndrillgrid_init_me(init_obj, app_obj):
            """
            This function is used to initialize the new
            object once it's created.

            :param init_obj: The new object.
            :param app_obj: The application (FlatCAMApp)
            :return: None
            """

            drills = []
            currenty = 0

            for row in range(args['rows']):
                currentx = 0

                for col in range(args['columns']):
                    point = Point(currentx + gridoffsetx, currenty + gridoffsety)
                    drills.append(point)
                    currentx = currentx + args['gridx']

                currenty = currenty + args['gridy']

            init_obj.tools = {
                '1': {
                    'tooldia': tooldia,
                    'drills': drills,
                    'solid_geometry': []
                }
            }
            init_obj.create_geometry()

        # Create the new object
        self.app.app_obj.new_object("excellon", outname, aligndrillgrid_init_me, plot=False)
